#
# Copyright (c) 2006, 2007 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Storm Object Relational Mapper.
#
# Storm is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Storm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""The Store interface to a database.

This module contains the highest-level ORM interface in Storm.
"""

from copy import copy
from weakref import WeakValueDictionary
from operator import itemgetter

from storm.info import get_cls_info, get_obj_info, set_obj_info
from storm.variables import Variable, LazyValue
from storm.expr import (
    Expr, Select, Insert, Update, Delete, Column, Count, Max, Min,
    Avg, Sum, Eq, And, Asc, Desc, compile_python, compare_columns, SQLRaw,
    Union, Except, Intersect, Alias, SetExpr)
from storm.exceptions import (
    WrongStoreError, NotFlushedError, OrderLoopError, UnorderedError,
    NotOneError, FeatureError, CompileError, LostObjectError, ClassInfoError)
from storm import Undef
from storm.cache import Cache
from storm.event import EventSystem


__all__ = ["Store", "AutoReload", "EmptyResultSet"]


PENDING_ADD = 1
PENDING_REMOVE = 2


class Store(object):
    """The Storm Store.

    This is the highest-level interface to a database. It manages
    transactions with L{commit} and L{rollback}, caching, high-level
    querying with L{find}, and more.

    Note that Store objects are not threadsafe. You should create one
    Store per thread in your application, passing them the same
    backend L{Database<storm.store.Database>} object.
    """

    _result_set_factory = None

    def __init__(self, database, cache=None):
        """
        @param database: The L{storm.database.Database} instance to use.
        @param cache: The cache to use.  Defaults to a L{Cache} instance.
        """
        self._event = EventSystem(self)
        self._connection = database.connect(self._event)
        self._alive = WeakValueDictionary()
        self._dirty = {}
        self._order = {} # (info, info) = count
        if cache is None:
            self._cache = Cache()
        else:
            self._cache = cache
        self._implicit_flush_block_count = 0
        self._sequence = 0 # Advisory ordering.

    @staticmethod
    def of(obj):
        """Get the Store that the object is associated with.

        If the given object has not yet been associated with a store,
        return None.
        """
        try:
            return get_obj_info(obj).get("store")
        except (AttributeError, ClassInfoError):
            return None

    def execute(self, statement, params=None, noresult=False):
        """Execute a basic query.

        This is just like L{storm.database.Database.execute}, except
        that a flush is performed first.
        """
        if self._implicit_flush_block_count == 0:
            self.flush()
        return self._connection.execute(statement, params, noresult)

    def close(self):
        """Close the connection."""
        self._connection.close()

    def commit(self):
        """Commit all changes to the database.

        This invalidates the cache, so all live objects will have data
        reloaded next time they are touched.
        """
        self.flush()
        self.invalidate()
        self._connection.commit()

    def rollback(self):
        """Roll back all outstanding changes, reverting to database state."""
        for obj_info in self._dirty:
            pending = obj_info.pop("pending", None)
            if pending is PENDING_ADD:
                # Object never got in the cache, so being "in the store"
                # has no actual meaning for it.
                del obj_info["store"]
            elif pending is PENDING_REMOVE:
                # Object never got removed, so it's still in the cache,
                # and thus should continue to resolve from now on.
                self._enable_lazy_resolving(obj_info)
        self._dirty.clear()
        self.invalidate()
        self._connection.rollback()

    def get(self, cls, key):
        """Get object of type cls with the given primary key from the database.

        If the object is alive the database won't be touched.

        @param cls: Class of the object to be retrieved.
        @param key: Primary key of object. May be a tuple for composed keys.

        @return: The object found with the given primary key, or None
            if no object is found.
        """

        if self._implicit_flush_block_count == 0:
            self.flush()

        if type(key) != tuple:
            key = (key,)

        cls_info = get_cls_info(cls)

        assert len(key) == len(cls_info.primary_key)

        primary_vars = []
        for column, variable in zip(cls_info.primary_key, key):
            if not isinstance(variable, Variable):
                variable = column.variable_factory(value=variable)
            primary_vars.append(variable)

        primary_values = tuple(var.get(to_db=True) for var in primary_vars)
        obj_info = self._alive.get((cls_info.cls, primary_values))
        if obj_info is not None:
            if obj_info.get("invalidated"):
                try:
                    self._validate_alive(obj_info)
                except LostObjectError:
                    return None
            return self._get_object(obj_info)

        where = compare_columns(cls_info.primary_key, primary_vars)

        select = Select(cls_info.columns, where,
                        default_tables=cls_info.table, limit=1)

        result = self._connection.execute(select)
        values = result.get_one()
        if values is None:
            return None
        return self._load_object(cls_info, result, values)

    def find(self, cls_spec, *args, **kwargs):
        """Perform a query.

        Some examples::

            store.find(Person, Person.name == u"Joe") --> all Persons named Joe
            store.find(Person, name=u"Joe") --> same
            store.find((Company, Person), Person.company_id == Company.id) -->
                iterator of tuples of Company and Person instances which are
                associated via the company_id -> Company relation.

        @param cls_spec: The class or tuple of classes whose
            associated tables will be queried.
        @param args: Instances of L{Expr}.
        @param kwargs: Mapping of simple column names to values or
            expressions to query for.

        @return: A L{ResultSet} of instances C{cls_spec}. If C{cls_spec}
            was a tuple, then an iterator of tuples of such instances.
        """
        if self._implicit_flush_block_count == 0:
            self.flush()
        find_spec = FindSpec(cls_spec)
        where = get_where_for_args(args, kwargs, find_spec.default_cls)
        return self._result_set_factory(self, find_spec, where)

    def using(self, *tables):
        """Specify tables to use explicitly.

        The L{find} method generally does a good job at figuring out
        the tables to query by itself, but in some cases it's useful
        to specify them explicitly.

        This is most often necessary when an explicit SQL join is
        required. An example follows::

            join = LeftJoin(Person, Person.id == Company.person_id)
            print list(store.using(Company, join).find((Company, Person)))

        The previous code snippet will produce an SQL statement
        somewhat similar to this, depending on your backend::

            SELECT company.id, employee.company_id, employee.id
            FROM company
            LEFT JOIN employee ON employee.company_id = company.id;

        @return: A L{TableSet}, which has a C{find} method similar to
            L{Store.find}.
        """
        return self._table_set(self, tables)

    def add(self, obj):
        """Add the given object to the store.

        The object will be inserted into the database if it has not
        yet been added.

        The C{added} event will be fired on the object info's event system.
        """
        self._event.emit("register-transaction")
        obj_info = get_obj_info(obj)

        store = obj_info.get("store")
        if store is not None and store is not self:
            raise WrongStoreError("%s is part of another store" % repr(obj))

        pending = obj_info.get("pending")

        if pending is PENDING_ADD:
            pass
        elif pending is PENDING_REMOVE:
            del obj_info["pending"]
            self._enable_lazy_resolving(obj_info)
            # obj_info.event.emit("added")
        elif store is None:
            obj_info["store"] = self
            obj_info["pending"] = PENDING_ADD
            self._set_dirty(obj_info)
            self._enable_lazy_resolving(obj_info)
            obj_info.event.emit("added")

        return obj

    def remove(self, obj):
        """Remove the given object from the store.

        The associated row will be deleted from the database.
        """
        self._event.emit("register-transaction")
        obj_info = get_obj_info(obj)

        if obj_info.get("store") is not self:
            raise WrongStoreError("%s is not in this store" % repr(obj))

        pending = obj_info.get("pending")

        if pending is PENDING_REMOVE:
            pass
        elif pending is PENDING_ADD:
            del obj_info["store"]
            del obj_info["pending"]
            self._set_clean(obj_info)
            self._disable_lazy_resolving(obj_info)
            obj_info.event.emit("removed")
        else:
            obj_info["pending"] = PENDING_REMOVE
            self._set_dirty(obj_info)
            self._disable_lazy_resolving(obj_info)
            obj_info.event.emit("removed")

    def reload(self, obj):
        """Reload the given object.

        The object will immediately have all of its data reset from
        the database. Any pending changes will be thrown away.
        """
        obj_info = get_obj_info(obj)
        cls_info = obj_info.cls_info
        if obj_info.get("store") is not self:
            raise WrongStoreError("%s is not in this store" % repr(obj))
        if "primary_vars" not in obj_info:
            raise NotFlushedError("Can't reload an object if it was "
                                  "never flushed")
        where = compare_columns(cls_info.primary_key, obj_info["primary_vars"])
        select = Select(cls_info.columns, where,
                        default_tables=cls_info.table, limit=1)
        result = self._connection.execute(select)
        values = result.get_one()
        self._set_values(obj_info, cls_info.columns, result, values)
        obj_info.checkpoint()
        self._set_clean(obj_info)

    def autoreload(self, obj=None):
        """Set an object or all objects to be reloaded automatically on access.

        When a database-backed attribute of one of the objects is
        accessed, the object will be reloaded entirely from the database.

        @param obj: If passed, only mark the given object for
            autoreload. Otherwise, all cached objects will be marked for
            autoreload.
        """
        self._mark_autoreload(obj, False)

    def invalidate(self, obj=None):
        """Set an object or all objects to be invalidated.

        This prevents Storm from returning the cached object without
        first verifying that the object is still available in the
        database.

        This should almost never be called by application code; it is
        only necessary if it is possible that an object has
        disappeared through some mechanism that Storm was unable to
        detect, like direct SQL statements within the current
        transaction that bypassed the ORM layer. The Store
        automatically invalidates all cached objects on transaction
        boundaries.
        """
        if obj is None:
            self._cache.clear()
        else:
            self._cache.remove(get_obj_info(obj))
        self._mark_autoreload(obj, True)

    def reset(self):
        """Reset this store, causing all future queries to return new objects.

        Beware this method: it breaks the assumption that there will never be
        two objects in memory which represent the same database object.

        This is useful if you've got in-memory changes to an object that you
        want to "throw out"; next time they're fetched the objects will be
        recreated, so in-memory modifications will not be in effect for future
        queries.
        """
        for obj_info in self._iter_alive():
            if "store" in obj_info:
                del obj_info["store"]
        self._alive.clear()
        self._dirty.clear()
        self._cache.clear()
        # The following line is untested, but then, I can't really find a way
        # to test it without whitebox.
        self._order.clear()


    def _mark_autoreload(self, obj=None, invalidate=False):
        if obj is None:
            obj_infos = self._iter_alive()
        else:
            obj_infos = (get_obj_info(obj),)
        for obj_info in obj_infos:
            cls_info = obj_info.cls_info
            for column in cls_info.columns:
                if id(column) not in cls_info.primary_key_idx:
                    obj_info.variables[column].set(AutoReload)
            if invalidate:
                # Marking an object with 'invalidated' means that we're
                # not sure if the object is actually in the database
                # anymore, so before the object is returned from the cache
                # (e.g. by a get()), the database should be queried to see
                # if the object's still there.
                obj_info["invalidated"] = True
        # We want to make sure we've marked all objects as invalidated and set
        # up their autoreloads before calling the invalidated hook on *any* of
        # them, because an invalidated hook might use other objects and we want
        # to prevent invalidation ordering issues.
        if invalidate:
            for obj_info in obj_infos:
                self._run_hook(obj_info, "__storm_invalidated__")

    def add_flush_order(self, before, after):
        """Explicitly specify the order of flushing two objects.

        When the next database flush occurs, the order of data
        modification statements will be ensured.

        @param before: The object to flush first.
        @param after: The object to flush after C{before}.
        """
        pair = (get_obj_info(before), get_obj_info(after))
        try:
            self._order[pair] += 1
        except KeyError:
            self._order[pair] = 1

    def remove_flush_order(self, before, after):
        """Cancel an explicit flush order specified with L{add_flush_order}.

        @param before: The C{before} object previously specified in a
            call to L{add_flush_order}.
        @param after: The C{after} object previously specified in a
            call to L{add_flush_order}.
        """
        pair = (get_obj_info(before), get_obj_info(after))
        self._order[pair] -= 1

    def flush(self):
        """Flush all dirty objects in cache to database.

        This method will first call the __storm_pre_flush__ hook of all dirty
        objects.  If more objects become dirty as a result of executing code
        in the hooks, the hook is also called on them.  The hook is only
        called once for each object.

        It will then flush each dirty object to the database, that is,
        execute the SQL code to insert/delete/update them.  After each
        object is flushed, the hook __storm_flushed__ is called on it,
        and if changes are made to the object it will get back to the
        dirty list, and be flushed again.

        Note that Storm will flush objects for you automatically, so you'll
        only need to call this method explicitly in very rare cases where
        normal flushing times are insufficient, such as when you want to
        make sure a database trigger gets run at a particular time.
        """
        self._event.emit("flush")

        # The _dirty list may change under us while we're running
        # the flush hooks, so we cannot just simply loop over it
        # once.  To prevent infinite looping we keep track of which
        # objects we've called the hook for using a `flushing` dict.
        flushing = {}
        while self._dirty:
            (obj_info, obj) = self._dirty.popitem()
            if obj_info not in flushing:
                flushing[obj_info] = obj
                self._run_hook(obj_info, "__storm_pre_flush__")
        self._dirty = flushing

        predecessors = {}
        for (before_info, after_info), n in self._order.iteritems():
            if n > 0:
                before_set = predecessors.get(after_info)
                if before_set is None:
                    predecessors[after_info] = set((before_info,))
                else:
                    before_set.add(before_info)

        key_func = itemgetter("sequence")

        # The external loop is important because items can get into the dirty
        # state while we're flushing objects, ...
        while self._dirty:
            # ... but we don't have to resort everytime an object is flushed,
            # so we have an internal loop too.  If no objects become dirty
            # during flush, this will clean self._dirty and the external loop
            # will exit too.
            sorted_dirty = sorted(self._dirty, key=key_func)
            while sorted_dirty:
                for i, obj_info in enumerate(sorted_dirty):
                    for before_info in predecessors.get(obj_info, ()):
                        if before_info in self._dirty:
                            break # A predecessor is still dirty.
                    else:
                        break # Found an item without dirty predecessors.
                else:
                    raise OrderLoopError("Can't flush due to ordering loop")
                del sorted_dirty[i]
                self._dirty.pop(obj_info, None)
                self._flush_one(obj_info)

        self._order.clear()

        # That's not stricly necessary, but prevents getting into bigints.
        self._sequence = 0

    def _flush_one(self, obj_info):
        cls_info = obj_info.cls_info

        pending = obj_info.pop("pending", None)

        if pending is PENDING_REMOVE:
            expr = Delete(compare_columns(cls_info.primary_key,
                                          obj_info["primary_vars"]),
                          cls_info.table)
            self._connection.execute(expr, noresult=True)

            # We're sure the cache is valid at this point.
            obj_info.pop("invalidated", None)

            self._disable_change_notification(obj_info)
            self._remove_from_alive(obj_info)
            del obj_info["store"]

        elif pending is PENDING_ADD:

            # Give a chance to the backend to process primary variables.
            self._connection.preset_primary_key(cls_info.primary_key,
                                                obj_info.primary_vars)

            changes = self._get_changes_map(obj_info, True)

            expr = Insert(changes, cls_info.table,
                          primary_columns=cls_info.primary_key,
                          primary_variables=obj_info.primary_vars)

            result = self._connection.execute(expr)

            # We're sure the cache is valid at this point. We just added
            # the object.
            obj_info.pop("invalidated", None)

            self._fill_missing_values(obj_info, obj_info.primary_vars, result)

            self._enable_change_notification(obj_info)
            self._add_to_alive(obj_info)

            obj_info.checkpoint()

        else:

            cached_primary_vars = obj_info["primary_vars"]
            primary_key_idx = cls_info.primary_key_idx

            changes = self._get_changes_map(obj_info)

            if changes:
                expr = Update(changes,
                              compare_columns(cls_info.primary_key,
                                              cached_primary_vars),
                              cls_info.table)
                self._connection.execute(expr, noresult=True)

                self._fill_missing_values(obj_info, obj_info.primary_vars)

                self._add_to_alive(obj_info)


            obj_info.checkpoint()

        self._run_hook(obj_info, "__storm_flushed__")

        obj_info.event.emit("flushed")

    def block_implicit_flushes(self):
        """Block implicit flushes from operations like execute()."""
        self._implicit_flush_block_count += 1

    def unblock_implicit_flushes(self):
        """Unblock implicit flushes from operations like execute()."""
        assert self._implicit_flush_block_count > 0
        self._implicit_flush_block_count -= 1

    def _get_changes_map(self, obj_info, adding=False):
        """Return a {column: variable} dictionary suitable for inserts/updates.

        @param obj_info: ObjectInfo to inspect for changes.
        @param adding: If true, any defined variables will be considered
                       a change and included in the returned map.
        """
        cls_info = obj_info.cls_info
        changes = {}
        select_variables = []
        for column in cls_info.columns:
            variable = obj_info.variables[column]
            if adding or variable.has_changed():
                if variable.is_defined():
                    changes[column] = variable
                else:
                    lazy_value = variable.get_lazy()
                    if isinstance(lazy_value, Expr):
                        if id(column) in cls_info.primary_key_idx:
                            select_variables.append(variable) # See below.
                            changes[column] = variable
                        else:
                            changes[column] = lazy_value

        # If we have any expressions in the primary variables, we
        # have to resolve them now so that we have the identity of
        # the inserted object available later.
        if select_variables:
            resolve_expr = Select([variable.get_lazy()
                                   for variable in select_variables])
            result = self._connection.execute(resolve_expr)
            for variable, value in zip(select_variables, result.get_one()):
                result.set_variable(variable, value)

        return changes

    def _fill_missing_values(self, obj_info, primary_vars, result=None):
        """Fill missing values in variables of the given obj_info.

        This method will verify which values are unset in obj_info,
        and set them to AutoReload, or if it's part of the primary
        key, query the database for the actual values.

        @param obj_info: ObjectInfo to have its values filled.
        @param primary_vars: Variables composing the primary key with
            up-to-date values (cached variables may be out-of-date when
            this method is called).
        @param result: If some value in the set of primary variables
            isn't defined, it must be retrieved from the database
            using database-dependent logic, which is provided by the
            backend in the result of the query which inserted the object.
        """
        cls_info = obj_info.cls_info

        cached_primary_vars = obj_info.get("primary_vars")
        primary_key_idx = cls_info.primary_key_idx
        missing_columns = []
        for column in cls_info.columns:
            variable = obj_info.variables[column]
            if not variable.is_defined():
                idx = primary_key_idx.get(id(column))
                if idx is not None:
                    if (cached_primary_vars is not None
                        and variable.get_lazy() is AutoReload):
                        # For auto-reloading a primary key, just
                        # get the value out of the cache.
                        variable.set(cached_primary_vars[idx].get())
                    else:
                        missing_columns.append(column)
                else:
                    # Any lazy values are overwritten here.  This value
                    # must have just been sent to the database, so this
                    # was already set there.
                    variable.set(AutoReload)

        if missing_columns:
            where = result.get_insert_identity(cls_info.primary_key,
                                               primary_vars)
            result = self._connection.execute(Select(missing_columns, where))
            self._set_values(obj_info, missing_columns,
                             result, result.get_one())

    def _validate_alive(self, obj_info):
        """Perform cache validation for the given obj_info."""
        where = compare_columns(obj_info.cls_info.primary_key,
                                obj_info["primary_vars"])
        result = self._connection.execute(Select(SQLRaw("1"), where))
        if not result.get_one():
            raise LostObjectError("Object is not in the database anymore")
        obj_info.pop("invalidated", None)

    def _load_object(self, cls_info, result, values):
        # _set_values() need the cls_info columns for the class of the
        # actual object, not from a possible wrapper (e.g. an alias).
        cls = cls_info.cls
        cls_info = get_cls_info(cls)

        # Prepare cache key.
        primary_vars = []
        columns = cls_info.columns

        for value in values:
            if value is not None:
                break
        else:
            # We've got a row full of NULLs, so consider that the object
            # wasn't found.  This is useful for joins, where non-existent
            # rows are represented like that.
            return None

        for i in cls_info.primary_key_pos:
            value = values[i]
            variable = columns[i].variable_factory(value=value, from_db=True)
            primary_vars.append(variable)

        # Lookup cache.
        primary_values = tuple(var.get(to_db=True) for var in primary_vars)
        obj_info = self._alive.get((cls, primary_values))

        if obj_info is not None:
            # Found object in cache, and it must be valid since the
            # primary key was extracted from result values.
            obj_info.pop("invalidated", None)

            # We're not sure if the obj is still in memory at this
            # point.  This will rebuild it if needed.
            obj = self._get_object(obj_info)

            # Take that chance and fill up any undefined variables
            # with fresh data, since we got it anyway.
            self._set_values(obj_info, cls_info.columns, result,
                             values, keep_defined=True)
        else:
            # Nothing found in the cache. Build everything from the ground.
            obj = cls.__new__(cls)

            obj_info = get_obj_info(obj)
            obj_info["store"] = self

            self._set_values(obj_info, cls_info.columns, result, values)

            obj_info.checkpoint()

            self._add_to_alive(obj_info)
            self._enable_change_notification(obj_info)
            self._enable_lazy_resolving(obj_info)

            self._run_hook(obj_info, "__storm_loaded__")

        return obj

    def _get_object(self, obj_info):
        """Return object for obj_info, rebuilding it if it's dead."""
        obj = obj_info.get_obj()
        if obj is None:
            cls = obj_info.cls_info.cls
            obj = cls.__new__(cls)
            obj_info.set_obj(obj)
            set_obj_info(obj, obj_info)
            # Re-enable change notification, as it may have been implicitely
            # disabled when the previous object has been collected
            self._enable_change_notification(obj_info)
            self._run_hook(obj_info, "__storm_loaded__")
        # Renew the cache.
        self._cache.add(obj_info)
        return obj

    @staticmethod
    def _run_hook(obj_info, hook_name):
        func = getattr(obj_info.get_obj(), hook_name, None)
        if func is not None:
            func()

    def _set_values(self, obj_info, columns, result, values,
                    keep_defined=False):
        if values is None:
            raise LostObjectError("Can't obtain values from the database "
                                  "(object got removed?)")
        obj_info.pop("invalidated", None)
        for column, value in zip(columns, values):
            variable = obj_info.variables[column]
            if keep_defined:
                if variable.is_defined():
                    continue
                lazy_value = variable.get_lazy()
                if not (lazy_value is None or lazy_value is AutoReload):
                    # This should *never* happen, because whenever we get
                    # to this point it should be after a flush() which
                    # updated the database with lazy values and then replaced
                    # them by AutoReload.  Letting this go through means
                    # we're blindly discarding an unknown lazy value and
                    # replacing it by the value from the database.
                    raise RuntimeError("Unexpected situation. "
                                       "Please contact the developers.")
            if value is None:
                variable.set(value, from_db=True)
            else:
                result.set_variable(variable, value)


    def _is_dirty(self, obj_info):
        return obj_info in self._dirty

    def _set_dirty(self, obj_info):
        if obj_info not in self._dirty:
            self._dirty[obj_info] = obj_info.get_obj()
            obj_info["sequence"] = self._sequence = self._sequence + 1

    def _set_clean(self, obj_info):
        self._dirty.pop(obj_info, None)

    def _iter_dirty(self):
        return self._dirty


    def _add_to_alive(self, obj_info):
        """Add an object to the set of known in-memory objects.

        When an object is added to the set of known in-memory objects,
        the key is built from a copy of the current variables that are
        part of the primary key.  This means that, when an object is
        retrieved from the database, these values may be used to get
        the cached object which is already in memory, even if it
        requested the primary key value to be changed.  For that reason,
        when changes to the primary key are flushed, the alive object
        key should also be updated to reflect these changes.

        In addition to tracking objects alive in memory, we have a strong
        reference cache which keeps a fixed number of last-used objects
        in-memory, to prevent further database access for recently fetched
        objects.
        """
        cls_info = obj_info.cls_info
        old_primary_vars = obj_info.get("primary_vars")
        if old_primary_vars is not None:
            old_primary_values = tuple(
                var.get(to_db=True) for var in old_primary_vars)
            self._alive.pop((cls_info.cls, old_primary_values), None)
        new_primary_vars = tuple(variable.copy()
                                 for variable in obj_info.primary_vars)
        new_primary_values = tuple(
            var.get(to_db=True) for var in new_primary_vars)
        self._alive[cls_info.cls, new_primary_values] = obj_info
        obj_info["primary_vars"] = new_primary_vars
        self._cache.add(obj_info)

    def _remove_from_alive(self, obj_info):
        """Remove an object from the cache.

        This method is only called for objects that were explicitly
        deleted and flushed.  Objects that are unused will get removed
        from the cache dictionary automatically by their weakref callbacks.
        """
        primary_vars = obj_info.get("primary_vars")
        if primary_vars is not None:
            self._cache.remove(obj_info)
            primary_values = tuple(var.get(to_db=True) for var in primary_vars)
            del self._alive[obj_info.cls_info.cls, primary_values]
            del obj_info["primary_vars"]

    def _iter_alive(self):
        return self._alive.values()

    def _enable_change_notification(self, obj_info):
        obj_info.event.emit("start-tracking-changes", self._event)
        obj_info.event.hook("changed", self._variable_changed)

    def _disable_change_notification(self, obj_info):
        obj_info.event.unhook("changed", self._variable_changed)
        obj_info.event.emit("stop-tracking-changes", self._event)

    def _variable_changed(self, obj_info, variable,
                          old_value, new_value, fromdb):
        # The fromdb check makes sure that values coming from the
        # database don't mark the object as dirty again.
        # XXX The fromdb check is untested. How to test it?
        if not fromdb:
            if new_value is not Undef and new_value is not AutoReload:
                if obj_info.get("invalidated"):
                    # This might be a previously alive object being
                    # updated.  Let's validate it now to improve debugging.
                    # This will raise LostObjectError if the object is gone.
                    self._validate_alive(obj_info)
                self._set_dirty(obj_info)


    def _enable_lazy_resolving(self, obj_info):
        obj_info.event.hook("resolve-lazy-value", self._resolve_lazy_value)

    def _disable_lazy_resolving(self, obj_info):
        obj_info.event.unhook("resolve-lazy-value", self._resolve_lazy_value)

    def _resolve_lazy_value(self, obj_info, variable, lazy_value):
        """Resolve a variable set to a lazy value when it's touched.

        This method is hooked into the obj_info to resolve variables
        set to lazy values when they're accessed.  It will first flush
        the store, and then set all variables set to AutoReload to
        their database values.
        """
        if lazy_value is not AutoReload and not isinstance(lazy_value, Expr):
            # It's not something we handle.
            return

        # XXX This will do it for now, but it should really flush
        #     just this single object and ones that it depends on.
        #     _flush_one() doesn't consider dependencies, so it may
        #     not be used directly.  Maybe allow flush(obj)?
        if self._implicit_flush_block_count == 0:
            self.flush()

        autoreload_columns = []
        for column in obj_info.cls_info.columns:
            if obj_info.variables[column].get_lazy() is AutoReload:
                autoreload_columns.append(column)

        if autoreload_columns:
            where = compare_columns(obj_info.cls_info.primary_key,
                                    obj_info["primary_vars"])
            result = self._connection.execute(Select(autoreload_columns, where))
            self._set_values(obj_info, autoreload_columns,
                             result, result.get_one())
            for column in autoreload_columns:
                obj_info.variables[column].checkpoint()


class ResultSet(object):
    """The representation of the results of a query.

    Note that having an instance of this class does not indicate that
    a database query has necessarily been made. Database queries are
    put off until absolutely necessary.

    Generally these should not be constructed directly, but instead
    retrieved from calls to L{Store.find}.
    """
    def __init__(self, store, find_spec,
                 where=Undef, tables=Undef, select=Undef):
        self._store = store
        self._find_spec = find_spec
        self._where = where
        self._tables = tables
        self._select = select
        self._order_by = find_spec.default_order
        self._offset = Undef
        self._limit = Undef
        self._distinct = False
        self._group_by = Undef
        self._having = Undef

    def copy(self):
        """Return a copy of this ResultSet object, with the same configuration.
        """
        result_set = object.__new__(self.__class__)
        result_set.__dict__.update(self.__dict__)
        return result_set

    def config(self, distinct=None, offset=None, limit=None):
        """Configure this result object in-place. All parameters are optional.

        @param distinct: Boolean enabling/disabling usage of the DISTINCT
            keyword in the query made.
        @param offset: Offset where results will start to be retrieved
            from the result set.
        @param limit: Limit the number of objects retrieved from the
            result set.

        @return: self (not a copy).
        """

        if distinct is not None:
            self._distinct = distinct
        if offset is not None:
            self._offset = offset
        if limit is not None:
            self._limit = limit
        return self

    def _get_select(self):
        if self._select is not Undef:
            if self._order_by is not Undef:
                self._select.order_by = self._order_by
            if self._limit is not Undef: # XXX UNTESTED!
                self._select.limit = self._limit
            if self._offset is not Undef: # XXX UNTESTED!
                self._select.offset = self._offset
            return self._select
        columns, default_tables = self._find_spec.get_columns_and_tables()
        return Select(columns, self._where, self._tables, default_tables,
                      self._order_by, offset=self._offset, limit=self._limit,
                      distinct=self._distinct, group_by=self._group_by,
                      having=self._having)

    def _load_objects(self, result, values):
        return self._find_spec.load_objects(self._store, result, values)

    def __iter__(self):
        """Iterate the results of the query.
        """
        result = self._store._connection.execute(self._get_select())
        for values in result:
            yield self._load_objects(result, values)

    def __getitem__(self, index):
        """Get an individual item by offset, or a range of items by slice.

        If a slice is used, a new L{ResultSet} will be return
        appropriately modified with OFFSET and LIMIT clauses.
        """
        if isinstance(index, (int, long)):
            if index == 0:
                result_set = self
            else:
                if self._offset is not Undef:
                    index += self._offset
                result_set = self.copy()
                result_set.config(offset=index, limit=1)
            obj = result_set.any()
            if obj is None:
                raise IndexError("Index out of range")
            return obj

        if not isinstance(index, slice):
            raise IndexError("Can't index ResultSets with %r" % (index,))
        if index.step is not None:
            raise IndexError("Stepped slices not yet supported: %r"
                             % (index.step,))

        offset = self._offset
        limit = self._limit

        if index.start is not None:
            if offset is Undef:
                offset = index.start
            else:
                offset += index.start
            if limit is not Undef:
                limit = max(0, limit - index.start)

        if index.stop is not None:
            if index.start is None:
                new_limit = index.stop
            else:
                new_limit = index.stop - index.start
            if limit is Undef or limit > new_limit:
                limit = new_limit

        return self.copy().config(offset=offset, limit=limit)

    def __contains__(self, item):
        """Check if an item is contained within the result set."""
        columns, values = self._find_spec.get_columns_and_values_for_item(item)

        if self._select is Undef and self._group_by is Undef:
            # No predefined select: adjust the where clause.
            dummy, default_tables = self._find_spec.get_columns_and_tables()
            where = [Eq(*pair) for pair in zip(columns, values)]
            if self._where is not Undef:
                where.append(self._where)
            select = Select(1, And(*where), self._tables,
                            default_tables)
        else:
            # Rewrite the predefined query and use it as a subquery.
            aliased_columns = [Alias(column, "_key%d" % index)
                               for (index, column) in enumerate(columns)]
            subquery = replace_columns(self._get_select(), aliased_columns)
            where = [Eq(*pair) for pair in zip(aliased_columns, values)]
            select = Select(1, And(*where), Alias(subquery, "_tmp"))

        result = self._store._connection.execute(select)
        return result.get_one() is not None

    def is_empty(self):
        """Return true if this L{ResultSet} contains no results."""
        subselect = self._get_select()
        subselect.limit = 1
        select = Select(1, tables=Alias(subselect, "_tmp"), limit=1)
        result = self._store._connection.execute(select)
        return (not result.get_one())

    def any(self):
        """Return a single item from the result set.

        See also one(), first(), and last().
        """
        select = self._get_select()
        select.limit = 1
        result = self._store._connection.execute(select)
        values = result.get_one()
        if values:
            return self._load_objects(result, values)
        return None

    def first(self):
        """Return the first item from an ordered result set.

        Will raise UnorderedError if the result set isn't ordered.

        See also last(), one(), and any().
        """
        if self._order_by is Undef:
            raise UnorderedError("Can't use first() on unordered result set")
        return self.any()

    def last(self):
        """Return the last item from an ordered result set.

        Will raise UnorderedError if the result set isn't ordered.

        See also first(), one(), and any().
        """
        if self._order_by is Undef:
            raise UnorderedError("Can't use last() on unordered result set")
        if self._limit is not Undef:
            raise FeatureError("Can't use last() with a slice "
                               "of defined stop index")
        select = self._get_select()
        select.offset = Undef
        select.limit = 1
        select.order_by = []
        for expr in self._order_by:
            if isinstance(expr, Desc):
                select.order_by.append(expr.expr)
            elif isinstance(expr, Asc):
                select.order_by.append(Desc(expr.expr))
            else:
                select.order_by.append(Desc(expr))
        result = self._store._connection.execute(select)
        values = result.get_one()
        if values:
            return self._load_objects(result, values)
        return None

    def one(self):
        """Return one item from a result set containing at most one item.

        Will raise NotOneError if the result set contains more than one item.

        See also first(), one(), and any().
        """
        select = self._get_select()
        # limit could be 1 due to slicing, for instance.
        if select.limit is not Undef and select.limit > 2:
            select.limit = 2
        result = self._store._connection.execute(select)
        values = result.get_one()
        if result.get_one():
            raise NotOneError("one() used with more than one result available")
        if values:
            return self._load_objects(result, values)
        return None

    def order_by(self, *args):
        """Specify the ordering of the results.

        The query will be modified appropriately with an ORDER BY clause.

        Ascending and descending order can be specified by wrapping
        the columns in L{Asc} and L{Desc}.

        @param args: One or more L{storm.expr.Column} objects.
        """
        if self._offset is not Undef or self._limit is not Undef:
            raise FeatureError("Can't reorder a sliced result set")
        self._order_by = args or Undef
        return self

    def remove(self):
        """Remove all rows represented by this ResultSet from the database.

        This is done efficiently with a DELETE statement, so objects
        are not actually loaded into Python.
        """
        if self._group_by is not Undef:
            raise FeatureError("Removing isn't supported after a "
                               " GROUP BY clause ")
        if self._offset is not Undef or self._limit is not Undef:
            raise FeatureError("Can't remove a sliced result set")
        if self._find_spec.default_cls_info is None:
            raise FeatureError("Removing not yet supported for tuple or "
                               "expression finds")
        if self._select is not Undef:
            raise FeatureError("Removing isn't supported with "
                               "set expressions (unions, etc)")
        result = self._store._connection.execute(
            Delete(self._where, self._find_spec.default_cls_info.table))
        return result.rowcount

    def group_by(self, *expr):
        """Group this ResultSet by the given expressions.

        @param expr: The expressions used in the GROUP BY statement.

        @return: self (not a copy).
        """
        if self._select is not Undef:
            raise FeatureError("Grouping isn't supported with "
                               "set expressions (unions, etc)")

        find_spec = FindSpec(expr)
        columns, dummy = find_spec.get_columns_and_tables()

        self._group_by = columns
        return self

    def having(self, *expr):
        """Filter result previously grouped by.

        @param expr: Instances of L{Expr}.

        @return: self (not a copy).
        """
        if self._group_by is Undef:
            raise FeatureError("having can only be called after group_by.")
        self._having = And(*expr)
        return self

    def _aggregate(self, aggregate_func, expr, column=None):
        if self._group_by is not Undef:
            raise FeatureError("Single aggregates aren't supported after a "
                               " GROUP BY clause ")
        columns, default_tables = self._find_spec.get_columns_and_tables()
        if (self._select is Undef and not self._distinct and
            self._offset is Undef and self._limit is Undef):
            select = Select(aggregate_func(expr), self._where,
                            self._tables, default_tables)
        else:
            if expr is Undef:
                aggregate = aggregate_func(expr)
            else:
                alias = Alias(expr, "_expr")
                columns.append(alias)
                aggregate = aggregate_func(alias)
            subquery = replace_columns(self._get_select(), columns)
            select = Select(aggregate, tables=Alias(subquery, "_tmp"))
        result = self._store._connection.execute(select)
        value = result.get_one()[0]
        variable_factory = getattr(column, "variable_factory", None)
        if variable_factory:
            variable = variable_factory(allow_none=True)
            result.set_variable(variable, value)
            return variable.get()
        return value

    def count(self, expr=Undef, distinct=False):
        """Get the number of objects represented by this ResultSet."""
        return int(self._aggregate(lambda expr: Count(expr, distinct), expr))

    def max(self, expr):
        """Get the highest value from an expression."""
        return self._aggregate(Max, expr, expr)

    def min(self, expr):
        """Get the lowest value from an expression."""
        return self._aggregate(Min, expr, expr)

    def avg(self, expr):
        """Get the average value from an expression."""
        value = self._aggregate(Avg, expr)
        if value is None:
            return value
        return float(value)

    def sum(self, expr):
        """Get the sum of all values in an expression."""
        return self._aggregate(Sum, expr, expr)

    def values(self, *columns):
        """Retrieve only the specified columns.

        This does not load full objects from the database into Python.

        @param columns: One or more L{storm.expr.Column} objects whose
            values will be fetched.
        @return: An iterator of tuples of the values for each column
            from each matching row in the database.
        """
        if not columns:
            raise FeatureError("values() takes at least one column "
                               "as argument")
        select = self._get_select()
        select.columns = columns
        result = self._store._connection.execute(select)
        if len(columns) == 1:
            variable = columns[0].variable_factory()
            for values in result:
                result.set_variable(variable, values[0])
                yield variable.get()
        else:
            variables = [column.variable_factory() for column in columns]
            for values in result:
                for variable, value in zip(variables, values):
                    result.set_variable(variable, value)
                yield tuple(variable.get() for variable in variables)

    def set(self, *args, **kwargs):
        """Update objects in the result set with the given arguments.

        This method will update all objects in the current result set
        to match expressions given as equalities or keyword arguments.
        These objects may still be in the database (an UPDATE is issued)
        or may be cached.

        For instance, C{result.set(Class.attr1 == 1, attr2=2)} will set
        C{attr1} to 1 and C{attr2} to 2, on all matching objects.
        """
        if self._group_by is not Undef:
            raise FeatureError("Setting isn't supported after a "
                               " GROUP BY clause ")

        if self._find_spec.default_cls_info is None:
            raise FeatureError("Setting isn't supported with tuple or "
                               "expression finds")
        if self._select is not Undef:
            raise FeatureError("Setting isn't supported with "
                               "set expressions (unions, etc)")

        if not (args or kwargs):
            return

        changes = {}
        cls = self._find_spec.default_cls_info.cls

        # For now only "Class.attr == var" is supported in args.
        for expr in args:
            if not isinstance(expr, Eq):
                raise FeatureError("Unsupported set expression: %r" %
                                   repr(expr))
            elif not isinstance(expr.expr1, Column):
                raise FeatureError("Unsupported left operand in set "
                                   "expression: %r" % repr(expr.expr1))
            elif not isinstance(expr.expr2, (Expr, Variable)):
                raise FeatureError("Unsupported right operand in set "
                                   "expression: %r" % repr(expr.expr2))
            changes[expr.expr1] = expr.expr2

        for key, value in kwargs.items():
            column = getattr(cls, key)
            if value is None:
                changes[column] = None
            elif isinstance(value, Expr):
                changes[column] = value
            else:
                changes[column] = column.variable_factory(value=value)

        expr = Update(changes, self._where,
                      self._find_spec.default_cls_info.table)
        self._store.execute(expr, noresult=True)

        try:
            cached = self.cached()
        except CompileError:
            # We are iterating through all objects in memory here, so
            # check if the object type matches to avoid trying to
            # invalidate a column that does not exist, on an unrelated
            # object.
            for obj_info in self._store._iter_alive():
                if obj_info.cls_info is self._find_spec.default_cls_info:
                    for column in changes:
                        obj_info.variables[column].set(AutoReload)
        else:
            changes = changes.items()
            for obj in cached:
                for column, value in changes:
                    variables = get_obj_info(obj).variables
                    if value is None:
                        pass
                    elif isinstance(value, Variable):
                        value = value.get()
                    elif isinstance(value, Expr):
                        # If the value is an Expression that means we
                        # can't compute it by ourselves: we rely on
                        # the database to compute it, so just set the
                        # value to AutoReload.
                        value = AutoReload
                    else:
                        value = variables[value].get()
                    variables[column].set(value)
                    variables[column].checkpoint()

    def cached(self):
        """Return matching objects from the cache for the current query."""
        if self._find_spec.default_cls_info is None:
            raise FeatureError("Cache finds not supported with tuples "
                               "or expressions")
        if self._tables is not Undef:
            raise FeatureError("Cache finds not supported with custom tables")
        if self._where is Undef:
            match = None
        else:
            match = compile_python.get_matcher(self._where)
            def get_column(column):
                return obj_info.variables[column].get()
        objects = []
        cls = self._find_spec.default_cls_info.cls
        for obj_info in self._store._iter_alive():
            try:
                if (obj_info.cls_info is self._find_spec.default_cls_info and
                    (match is None or match(get_column))):
                    objects.append(self._store._get_object(obj_info))
            except LostObjectError:
                pass # This may happen when resolving lazy values
                     # in get_column().
        return objects

    def find(self, *args, **kwargs):
        """Perform a query on objects within this result set.

        This is analogous to L{Store.find}, although it doesn't take a
        C{cls_spec} argument, instead using the same tables as the
        existing result set, and restricts the results to those in
        this set.

        @param args: Instances of L{Expr}.
        @param kwargs: Mapping of simple column names to values or
            expressions to query for.

        @return: A L{ResultSet} of matching instances.
        """
        if self._select is not Undef:
            raise FeatureError("Can't query set expressions")
        if self._offset is not Undef or self._limit is not Undef:
            raise FeatureError("Can't query a sliced result set")
        if self._group_by is not Undef:
            raise FeatureError("Can't query grouped result sets")

        result_set = self.copy()
        extra_where = get_where_for_args(
            args, kwargs, self._find_spec.default_cls)
        if extra_where is not Undef:
            if result_set._where is Undef:
                result_set._where = extra_where
            else:
                result_set._where = And(result_set._where, extra_where)
        return result_set

    def _set_expr(self, expr_cls, other, all=False):
        if not self._find_spec.is_compatible(other._find_spec):
            raise FeatureError("Incompatible results for set operation")

        expr = expr_cls(self._get_select(), other._get_select(), all=all)
        return ResultSet(self._store, self._find_spec, select=expr)

    def union(self, other, all=False):
        """Get the L{Union} of this result set and another.

        @param all: If True, include duplicates.
        """
        if isinstance(other, EmptyResultSet):
            return self
        return self._set_expr(Union, other, all)

    def difference(self, other, all=False):
        """Get the difference, using L{Except}, of this result set and another.

        @param all: If True, include duplicates.
        """
        if isinstance(other, EmptyResultSet):
            return self
        return self._set_expr(Except, other, all)

    def intersection(self, other, all=False):
        """Get the L{Intersection} of this result set and another.

        @param all: If True, include duplicates.
        """
        if isinstance(other, EmptyResultSet):
            return other
        return self._set_expr(Intersect, other, all)


class EmptyResultSet(object):
    """An object that looks like a L{ResultSet} but represents no rows.

    This is convenient for application developers who want to provide
    a method which is guaranteed to return a L{ResultSet}-like object
    but which, in certain cases, knows there is no point in querying
    the database. For example::

        def get_people(self, ids):
            if not ids:
                return EmptyResultSet()
            return store.find(People, People.id.is_in(ids))

    The methods on EmptyResultSet (L{one}, L{config}, L{union}, etc)
    are meant to emulate a L{ResultSet} which has matched no rows.
    """

    def __init__(self, ordered=False):
        self._order_by = ordered

    def _get_select(self):
        return Select(SQLRaw("1"), SQLRaw("1 = 2"))

    def copy(self):
        result = EmptyResultSet(self._order_by)
        return result

    def config(self, distinct=None, offset=None, limit=None):
        pass

    def __iter__(self):
        return
        yield None

    def __getitem__(self, index):
        return self.copy()

    def __contains__(self, item):
        return False

    def is_empty(self):
        return True

    def any(self):
        return None

    def first(self):
        if self._order_by:
            return None
        raise UnorderedError("Can't use first() on unordered result set")

    def last(self):
        if self._order_by:
            return None
        raise UnorderedError("Can't use last() on unordered result set")

    def one(self):
        return None

    def order_by(self, *args):
        self._order_by = True
        return self

    def remove(self):
        return 0

    def count(self, expr=Undef, distinct=False):
        return 0

    def max(self, column):
        return None

    def min(self, column):
        return None

    def avg(self, column):
        return None

    def sum(self, column):
        return None

    def values(self, *columns):
        if not columns:
            raise FeatureError("values() takes at least one column "
                               "as argument")
        return
        yield None

    def set(self, *args, **kwargs):
        pass

    def cached(self):
        return []

    def find(self, *args, **kwargs):
        return self

    def union(self, other):
        if isinstance(other, EmptyResultSet):
            return self
        return other.union(self)

    def difference(self, other):
        return self

    def intersection(self, other):
        return self


class TableSet(object):
    """The representation of a set of tables which can be queried at once.

    This will typically be constructed by a call to L{Store.using}.
    """

    def __init__(self, store, tables):
        self._store = store
        self._tables = tables

    def find(self, cls_spec, *args, **kwargs):
        """Perform a query on the previously specified tables.

        This is identical to L{Store.find} except that the tables are
        explicitly specified instead of relying on inference.

        @return: A L{ResultSet}.
        """
        if self._store._implicit_flush_block_count == 0:
            self._store.flush()
        find_spec = FindSpec(cls_spec)
        where = get_where_for_args(args, kwargs, find_spec.default_cls)
        return self._store._result_set_factory(self._store, find_spec,
                                               where, self._tables)


Store._result_set_factory = ResultSet
Store._table_set = TableSet


class FindSpec(object):
    """The set of tables or expressions in the result of L{Store.find}."""

    def __init__(self, cls_spec):
        self.is_tuple = type(cls_spec) == tuple
        if not self.is_tuple:
            cls_spec = (cls_spec,)

        info = []
        for item in cls_spec:
            if isinstance(item, Expr):
                info.append((True, item))
            else:
                info.append((False, get_cls_info(item)))
        self._cls_spec_info = tuple(info)

        # Do we have a single non-expression item here?
        if not self.is_tuple and not info[0][0]:
            self.default_cls = cls_spec[0]
            self.default_cls_info = info[0][1]
            self.default_order = self.default_cls_info.default_order
        else:
            self.default_cls = None
            self.default_cls_info = None
            self.default_order = Undef

    def get_columns_and_tables(self):
        columns = []
        default_tables = []
        for is_expr, info in self._cls_spec_info:
            if is_expr:
                columns.append(info)
                if isinstance(info, Column):
                    default_tables.append(info.table)
            else:
                columns.extend(info.columns)
                default_tables.append(info.table)
        return columns, default_tables

    def is_compatible(self, find_spec):
        """Return True if this FindSpec is compatible with a second one."""
        if self.is_tuple != find_spec.is_tuple:
            return False
        if len(self._cls_spec_info) != len(find_spec._cls_spec_info):
            return False
        for (is_expr1, info1), (is_expr2, info2) in zip(
            self._cls_spec_info, find_spec._cls_spec_info):
            if is_expr1 != is_expr2:
                return False
            if info1 is not info2:
                return False
        return True

    def load_objects(self, store, result, values):
        objects = []
        values_start = values_end = 0
        for is_expr, info in self._cls_spec_info:
            if is_expr:
                values_end += 1
                variable = getattr(info, "variable_factory", Variable)(
                    value=values[values_start], from_db=True)
                objects.append(variable.get())
            else:
                values_end += len(info.columns)
                obj = store._load_object(info, result,
                                         values[values_start:values_end])
                objects.append(obj)
            values_start = values_end
        if self.is_tuple:
            return tuple(objects)
        else:
            return objects[0]

    def get_columns_and_values_for_item(self, item):
        """Generate a comparison expression with the given item."""
        if isinstance(item, tuple):
            if not self.is_tuple:
                raise TypeError("Find spec does not expect tuples.")
        else:
            if self.is_tuple:
                raise TypeError("Find spec expects tuples.")
            item = (item,)

        columns = []
        values = []
        for (is_expr, info), value in zip(self._cls_spec_info, item):
            if is_expr:
                if not isinstance(value, (Expr, Variable)) and (
                    value is not None):
                    value = getattr(info, "variable_factory", Variable)(
                        value=value)
                columns.append(info)
                values.append(value)
            else:
                obj_info = get_obj_info(value)
                if obj_info.cls_info != info:
                    raise TypeError("%r does not match %r" % (value, info))
                columns.extend(info.primary_key)
                values.extend(obj_info.primary_vars)
        return columns, values


def get_where_for_args(args, kwargs, cls=None):
    equals = list(args)
    if kwargs:
        if cls is None:
            raise FeatureError("Can't determine class that keyword "
                               "arguments are associated with")
        for key, value in kwargs.items():
            equals.append(getattr(cls, key) == value)
    if equals:
        return And(*equals)
    return Undef


def replace_columns(expr, columns):
    if isinstance(expr, Select):
        select = copy(expr)
        select.columns = columns
        # Remove the ordering if it won't affect the result of the query.
        if select.limit is Undef and select.offset is Undef:
            select.order_by = Undef
        return select
    elif isinstance(expr, SetExpr):
        # The ORDER BY clause might refer to columns we have replaced.
        # Luckily we can ignore it if there is no limit/offset.
        if expr.order_by is not Undef and (
            expr.limit is not Undef or expr.offset is not Undef):
            raise FeatureError(
                "__contains__() does not yet support set "
                "expressions that combine ORDER BY with "
                "LIMIT/OFFSET")
        subexprs = [replace_columns(subexpr, columns)
                    for subexpr in expr.exprs]
        return expr.__class__(
            all=expr.all, limit=expr.limit, offset=expr.offset,
            *subexprs)
    else:
        raise FeatureError(
            "__contains__() does not yet support %r expressions"
            % (expr.__class__,))


class AutoReload(LazyValue):
    """A marker for reloading a single value.

    Often this will be used to specify that a specific attribute
    should be loaded from the database on the next access, like so::

        storm_object.property = AutoReload

    On the next access to C{storm_object.property}, the value will be
    loaded from the database.

    It is also often used as a default value for a property::

        class Person(object):
            __storm_table__ = "person"
            id = Int(allow_none=False, default=AutoReload)

        person = store.add(Person)
        person.id # gets the attribute from the database.
    """
    pass

AutoReload = AutoReload()
