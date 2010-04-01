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
import weakref

from storm.exceptions import WrongStoreError, NoStoreError, ClassInfoError
from storm.store import Store, get_where_for_args, LostObjectError
from storm.variables import LazyValue
from storm.expr import (
    Select, Column, Exists, ComparableExpr, LeftJoin, Not, SQLRaw,
    compare_columns, compile)
from storm.info import get_cls_info, get_obj_info


__all__ = ["Reference", "ReferenceSet", "Proxy"]


class LazyAttribute(object):
    """
    This descriptor will call the named attribute builder to
    initialize the given attribute on first access.  It avoids
    having a test at every single place where the attribute is
    touched when lazy initialization is wanted, and prevents
    paying the price of a normal property when classes are
    seldomly instantiated (the case of references).
    """

    def __init__(self, attr, attr_builder):
        self._attr = attr
        self._attr_builder = attr_builder

    def __get__(self, obj, cls=None):
        getattr(obj, self._attr_builder)()
        return getattr(obj, self._attr)


class PendingReferenceValue(LazyValue):
    """Lazy value to be used as a marker for unflushed foreign keys.

    When a reference is set to an object which is still unflushed,
    the foreign key in the local object remains set to this value
    until the object is flushed.
    """

PendingReferenceValue = PendingReferenceValue()


class Reference(object):
    """Descriptor for one-to-one relationships.

    This is typically used when the class that it is being defined on
    has a foreign key onto another table::

        class OtherGuy(object):
            ...
            id = Int()

        class MyGuy(object):
            ...
            other_guy_id = Int()
            other_guy = Reference(other_guy_id, OtherGuy.id)

    but can also be used for backwards references, where OtherGuy's
    table has a foreign key onto the class that you want this property
    on::

        class OtherGuy(object):
            ...
            my_guy_id = Int() # in the database, a foreign key to my_guy.id

        class MyGuy(object):
            ...
            id = Int()
            other_guy = Reference(id, OtherGuy.my_guy_id, on_remote=True)

    In both cases, C{MyGuy().other_guy} will resolve to the
    C{OtherGuy} instance which is linked to it. In the first case, it
    will be the C{OtherGuy} instance whose C{id} is equivalent to the
    C{MyGuy}'s C{other_guy_id}; in the second, it'll be the
    C{OtherGuy} instance whose C{my_guy_id} is equivalent to the
    C{MyGuy}'s C{id}.

    Assigning to the property, for example with C{MyGuy().other_guy =
    OtherGuy()}, will link the objects and update either
    C{MyGuy.other_guy_id} or C{OtherGuy.my_guy_id} accordingly.
    """

    # Must initialize _relation later because we don't want to resolve
    # string references at definition time, since classes refered to might
    # not be available yet.  Notice that this attribute is "public" to the
    # Proxy class and the SQLObject wrapper.  It's still underlined because
    # it's *NOT* part of the public API of Storm (we'll modify it without
    # warnings!).
    _relation = LazyAttribute("_relation", "_build_relation")

    def __init__(self, local_key, remote_key, on_remote=False):
        """
        Create a Reference property.

        @param local_key: The sibling column which is the foreign key
            onto C{remote_key}. (unless C{on_remote} is passed; see
            below).
        @param remote_key: The column on the referred-to object which
            will have the same value as that for C{local_key} when
            resolved on an instance.
        @param on_remote: If specified, then the reference is
            backwards: It is the C{remote_key} which is a foreign key
            onto C{local_key}.
        """
        self._local_key = local_key
        self._remote_key = remote_key
        self._on_remote = on_remote
        self._cls = None

    def __get__(self, local, cls=None):
        if local is not None:
            # Don't use local here, as it might be security proxied.
            local = get_obj_info(local).get_obj()

        if self._cls is None:
            self._cls = _find_descriptor_class(cls or local.__class__, self)

        if local is None:
            return self

        remote = self._relation.get_remote(local)
        if remote is not None:
            return remote

        if self._relation.local_variables_are_none(local):
            return None

        store = Store.of(local)
        if store is None:
            return None

        if self._relation.remote_key_is_primary:
            remote = store.get(self._relation.remote_cls,
                               self._relation.get_local_variables(local))
        else:
            where = self._relation.get_where_for_remote(local)
            result = store.find(self._relation.remote_cls, where)
            remote = result.one()

        if remote is not None:
            self._relation.link(local, remote)

        return remote

    def __set__(self, local, remote):
        # Don't use local here, as it might be security proxied or something.
        local = get_obj_info(local).get_obj()

        if self._cls is None:
            self._cls = _find_descriptor_class(local.__class__, self)

        if remote is None:
            if self._on_remote:
                remote = self.__get__(local)
                if remote is None:
                    return
            else:
                remote = self._relation.get_remote(local)
            if remote is None:
                remote_info = None
            else:
                remote_info = get_obj_info(remote)
            self._relation.unlink(get_obj_info(local), remote_info, True)
        else:
            # Don't use remote here, as it might be
            # security proxied or something.
            try:
                remote = get_obj_info(remote).get_obj()
            except ClassInfoError:
                pass # It might fail when remote is a tuple or a raw value.
            self._relation.link(local, remote, True)

    def _build_relation(self):
        resolver = PropertyResolver(self, self._cls)
        self._local_key = resolver.resolve(self._local_key)
        self._remote_key = resolver.resolve(self._remote_key)
        self._relation = Relation(self._local_key, self._remote_key,
                                  False, self._on_remote)

    def __eq__(self, other):
        return self._relation.get_where_for_local(other)

    def __ne__(self, other):
        return Not(self == other)


class ReferenceSet(object):

    # Must initialize later because we don't want to resolve string
    # references at definition time, since classes refered to might
    # not be available yet.
    _relation1 = LazyAttribute("_relation1", "_build_relations")
    _relation2 = LazyAttribute("_relation2", "_build_relations")

    def __init__(self, local_key1, remote_key1,
                 remote_key2=None, local_key2=None, order_by=None):
        self._local_key1 = local_key1
        self._remote_key1 = remote_key1
        self._remote_key2 = remote_key2
        self._local_key2 = local_key2
        self._order_by = order_by
        self._cls = None

    def __get__(self, local, cls=None):
        if local is not None:
            # Don't use local here, as it might be security proxied.
            local = get_obj_info(local).get_obj()

        if self._cls is None:
            self._cls = _find_descriptor_class(cls or local.__class__, self)

        if local is None:
            return self

        #store = Store.of(local)
        #if store is None:
        #    return None

        if self._relation2 is None:
            return BoundReferenceSet(self._relation1, local, self._order_by)
        else:
            return BoundIndirectReferenceSet(self._relation1,
                                             self._relation2, local,
                                             self._order_by)

    def _build_relations(self):
        resolver = PropertyResolver(self, self._cls)

        self._local_key1 = resolver.resolve(self._local_key1)
        self._remote_key1 = resolver.resolve(self._remote_key1)
        self._relation1 = Relation(self._local_key1, self._remote_key1,
                                   True, True)

        if self._local_key2 and self._remote_key2:
            self._local_key2 = resolver.resolve(self._local_key2)
            self._remote_key2 = resolver.resolve(self._remote_key2)
            self._relation2 = Relation(self._local_key2, self._remote_key2,
                                       True, True)
        else:
            self._relation2 = None


class BoundReferenceSetBase(object):

    def find(self, *args, **kwargs):
        store = Store.of(self._local)
        if store is None:
            raise NoStoreError("Can't perform operation without a store")
        where = self._get_where_clause()
        result = store.find(self._target_cls, where, *args, **kwargs)
        if self._order_by is not None:
            result.order_by(self._order_by)
        return result

    def __iter__(self):
        return self.find().__iter__()

    def __contains__(self, item):
        return item in self.find()

    def first(self, *args, **kwargs):
        return self.find(*args, **kwargs).first()

    def last(self, *args, **kwargs):
        return self.find(*args, **kwargs).last()

    def any(self, *args, **kwargs):
        return self.find(*args, **kwargs).any()

    def one(self, *args, **kwargs):
        return self.find(*args, **kwargs).one()

    def values(self, *columns):
        return self.find().values(*columns)

    def order_by(self, *args):
        return self.find().order_by(*args)

    def count(self):
        return self.find().count()


class BoundReferenceSet(BoundReferenceSetBase):

    def __init__(self, relation, local, order_by):
        self._relation = relation
        self._local = local
        self._target_cls = self._relation.remote_cls
        self._order_by = order_by

    def _get_where_clause(self):
        return self._relation.get_where_for_remote(self._local)

    def clear(self, *args, **kwargs):
        set_kwargs = {}
        for remote_column in self._relation.remote_key:
            set_kwargs[remote_column.name] = None
        store = Store.of(self._local)
        if store is None:
            raise NoStoreError("Can't perform operation without a store")
        where = self._relation.get_where_for_remote(self._local)
        store.find(self._target_cls, where, *args, **kwargs).set(**set_kwargs)

    def add(self, remote):
        self._relation.link(self._local, remote, True)

    def remove(self, remote):
        self._relation.unlink(get_obj_info(self._local),
                              get_obj_info(remote), True)


class BoundIndirectReferenceSet(BoundReferenceSetBase):

    def __init__(self, relation1, relation2, local, order_by):
        self._relation1 = relation1
        self._relation2 = relation2
        self._local = local
        self._order_by = order_by

        self._target_cls = relation2.local_cls
        self._link_cls = relation1.remote_cls

    def _get_where_clause(self):
        return (self._relation1.get_where_for_remote(self._local) &
                self._relation2.get_where_for_join())

    def clear(self, *args, **kwargs):
        store = Store.of(self._local)
        if store is None:
            raise NoStoreError("Can't perform operation without a store")
        where = self._relation1.get_where_for_remote(self._local)
        if args or kwargs:
            filter = get_where_for_args(args, kwargs, self._target_cls)
            join = self._relation2.get_where_for_join()
            table = get_cls_info(self._target_cls).table
            where &= Exists(Select(SQLRaw("*"), join & filter, tables=table))
        store.find(self._link_cls, where).remove()

    def add(self, remote):
        link = self._link_cls()
        self._relation1.link(self._local, link, True)
        # Don't use remote here, as it might be security proxied or something.
        remote = get_obj_info(remote).get_obj()
        self._relation2.link(remote, link, True)

    def remove(self, remote):
        store = Store.of(self._local)
        if store is None:
            raise NoStoreError("Can't perform operation without a store")
        # Don't use remote here, as it might be security proxied or something.
        remote = get_obj_info(remote).get_obj()
        where = (self._relation1.get_where_for_remote(self._local) &
                 self._relation2.get_where_for_remote(remote))
        store.find(self._link_cls, where).remove()


class Proxy(ComparableExpr):
    """Proxy exposes a referred object's column as a local column.

    For example::

      class Foo(object):
          bar_id = Int()
          bar = Reference(bar_id, Bar.id)
          bar_title = Proxy(bar, Bar.title)

    For most uses, Foo.bar_title should behave as if it were
    a native property of Foo.
    """

    class RemoteProp(object):
        """
        This descriptor will resolve and set the _remote_prop attribute
        when it's first used. It avoids having a test at every single
        place where the attribute is touched.
        """
        def __get__(self, obj, cls=None):
            resolver = PropertyResolver(obj, obj._cls)
            obj._remote_prop = resolver.resolve_one(obj._unresolved_prop)
            return obj._remote_prop

    _remote_prop = RemoteProp()

    def __init__(self, reference, remote_prop):
        self._reference = reference
        self._unresolved_prop = remote_prop
        self._cls = None

    def __get__(self, obj, cls=None):
        if self._cls is None:
            self._cls = _find_descriptor_class(cls, self)
        if obj is None:
            return self
        # Have you counted how many descriptors we're dealing with here? ;-)
        return self._remote_prop.__get__(self._reference.__get__(obj))

    def __set__(self, obj, value):
        return self._remote_prop.__set__(self._reference.__get__(obj), value)

    @property
    def variable_factory(self):
        return self._remote_prop.variable_factory

@compile.when(Proxy)
def compile_proxy(compile, proxy, state):
    # Inject the join between the table of the class holding the proxy
    # and the table of the class which is the target of the reference.
    left_join = LeftJoin(proxy._reference._relation.local_cls,
                         proxy._remote_prop.table,
                         proxy._reference._relation.get_where_for_join())
    state.auto_tables.append(left_join)

    # And compile the remote property normally.
    return compile(proxy._remote_prop, state)


class Relation(object):

    def __init__(self, local_key, remote_key, many, on_remote):
        assert type(local_key) is tuple and type(remote_key) is tuple

        self.local_key = local_key
        self.remote_key = remote_key

        self.local_cls = getattr(self.local_key[0], "cls", None)
        self.remote_cls = self.remote_key[0].cls
        self.remote_key_is_primary = False

        primary_key = get_cls_info(self.remote_cls).primary_key
        if len(primary_key) == len(self.remote_key):
            for column1, column2 in zip(self.remote_key, primary_key):
                if column1.name != column2.name:
                    break
            else:
                self.remote_key_is_primary = True

        self.many = many
        self.on_remote = on_remote

        # XXX These should probably be weak dictionaries.
        self._local_columns = {}
        self._remote_columns = {}

        self._l_to_r = {}
        self._r_to_l = {}

    def get_remote(self, local):
        """Return the remote object for this relation, using the local cache.

        If the object in the cache is invalidated, we validate it again to
        check if it's still in the database.
        """
        local_info = get_obj_info(local)
        try:
            obj = local_info[self]["remote"]
        except KeyError:
            return None
        remote_info = get_obj_info(obj)
        if remote_info.get("invalidated"):
            try:
                Store.of(obj)._validate_alive(remote_info)
            except LostObjectError:
                return None
        return obj

    def get_where_for_remote(self, local):
        """Generate a column comparison expression for reference properties.

        The returned expression may be used to find objects of the I{remote}
        type referring to C{local}.
        """
        local_variables = self.get_local_variables(local)
        for variable in local_variables:
            if not variable.is_defined():
                Store.of(local).flush()
                break
        return compare_columns(self.remote_key, local_variables)

    def get_where_for_local(self, other):
        """Generate a column comparison expression for reference properties.

        The returned expression may be used to find objects of the I{local}
        type referring to C{other}.

        It handles the following cases::

            Class.reference == obj
            Class.reference == obj.id
            Class.reference == (obj.id1, obj.id2)

        Where the right-hand side is the C{other} object given.
        """
        try:
            obj_info = get_obj_info(other)
        except ClassInfoError:
            if type(other) is not tuple:
                remote_variables = (other,)
            else:
                remote_variables = other
        else:
            # Don't use other here, as it might be
            # security proxied or something.
            other = get_obj_info(other).get_obj()
            remote_variables = self.get_remote_variables(other)
        return compare_columns(self.local_key, remote_variables)

    def get_where_for_join(self):
        return compare_columns(self.local_key, self.remote_key)

    def get_local_variables(self, local):
        local_info = get_obj_info(local)
        return tuple(local_info.variables[column]
                     for column in self._get_local_columns(local.__class__))

    def local_variables_are_none(self, local):
        """Return true if all variables of the local key have None values."""
        local_info = get_obj_info(local)
        for column in self._get_local_columns(local.__class__):
            if local_info.variables[column].get() is not None:
                return False
        return True

    def get_remote_variables(self, remote):
        remote_info = get_obj_info(remote)
        return tuple(remote_info.variables[column]
                     for column in self._get_remote_columns(remote.__class__))

    def link(self, local, remote, setting=False):
        """Link objects to represent their relation.

        @param local: Object representing the I{local} side of the reference.

        @param remote: Object representing the I{remote} side of the reference,
            or the actual value to be set as the local key.

        @param setting: Pass true when the relationship is being newly created.
        """
        local_info = get_obj_info(local)

        try:
            remote_info = get_obj_info(remote)
        except ClassInfoError:
            # Must be a plain key. Just set it.
            # XXX I guess this is broken if self.on_remote is True.
            local_variables = self.get_local_variables(local)
            if type(remote) is not tuple:
                remote = (remote,)
            assert len(remote) == len(local_variables)
            for variable, value in zip(local_variables, remote):
                variable.set(value)
            return

        local_store = Store.of(local)
        remote_store = Store.of(remote)

        if setting:
            if local_store is None:
                if remote_store is None:
                    local_info.event.hook("added", self._add_all, local_info)
                    remote_info.event.hook("added", self._add_all, local_info)
                else:
                    remote_store.add(local)
                    local_store = remote_store
            elif remote_store is None:
                local_store.add(remote)
            elif local_store is not remote_store:
                raise WrongStoreError("%r and %r cannot be linked because they "
                                      "are in different stores." %
                                      (local, remote))

        # In cases below, we maintain a reference to the remote object
        # to make sure it won't get deallocated while the link is active.
        relation_data = local_info.get(self)
        if self.many:
            if relation_data is None:
                relation_data = local_info[self] = {"remote":
                                                    {remote_info: remote}}
            else:
                relation_data["remote"][remote_info] = remote
        else:
            if relation_data is None:
                relation_data = local_info[self] = {"remote": remote}
            else:
                old_remote = relation_data.get("remote")
                if old_remote is not None:
                    self.unlink(local_info, get_obj_info(old_remote))
                relation_data["remote"] = remote

        if setting:
            local_vars = local_info.variables
            remote_vars = remote_info.variables
            pairs = zip(self._get_local_columns(local.__class__),
                        self.remote_key)
            if self.on_remote:
                local_has_changed = False
                for local_column, remote_column in pairs:
                    local_var = local_vars[local_column]
                    if not local_var.is_defined():
                        remote_vars[remote_column].set(PendingReferenceValue)
                    else:
                        remote_vars[remote_column].set(local_var.get())
                    if local_var.has_changed():
                        local_has_changed = True

                if local_has_changed:
                    self._add_flush_order(local_info, remote_info)

                local_info.event.hook("changed", self._track_local_changes,
                                      remote_info)
                local_info.event.hook("flushed", self._break_on_local_flushed,
                                      remote_info)
                #local_info.event.hook("removed", self._break_on_local_removed,
                #                      remote_info)
                remote_info.event.hook("removed", self._break_on_remote_removed,
                                       weakref.ref(local_info))
            else:
                remote_has_changed = False
                for local_column, remote_column in pairs:
                    remote_var = remote_vars[remote_column]
                    if not remote_var.is_defined():
                        local_vars[local_column].set(PendingReferenceValue)
                    else:
                        local_vars[local_column].set(remote_var.get())
                    if remote_var.has_changed():
                        remote_has_changed = True

                if remote_has_changed:
                    self._add_flush_order(local_info, remote_info,
                                          remote_first=True)

                remote_info.event.hook("changed", self._track_remote_changes,
                                       local_info)
                remote_info.event.hook("flushed", self._break_on_remote_flushed,
                                       local_info)
                #local_info.event.hook("removed", self._break_on_remote_removed,
                #                      local_info)

                local_info.event.hook("changed", self._break_on_local_diverged,
                                      remote_info)
        else:
            local_info.event.hook("changed", self._break_on_local_diverged,
                                  remote_info)
            remote_info.event.hook("changed", self._break_on_remote_diverged,
                                   weakref.ref(local_info))
            if self.on_remote:
                remote_info.event.hook("removed", self._break_on_remote_removed,
                                       weakref.ref(local_info))

    def unlink(self, local_info, remote_info, setting=False):
        """Break the relation between the local and remote objects.

        @param setting: If true objects will be changed to persist breakage.
        """
        unhook = False
        relation_data = local_info.get(self)
        if relation_data is not None:
            if self.many:
                remote_infos = relation_data["remote"]
                if remote_info in remote_infos:
                    remote_infos.pop(remote_info, None)
                    unhook = True
            else:
                if relation_data.pop("remote", None) is not None:
                    unhook = True

        if unhook:
            local_store = Store.of(local_info)

            local_info.event.unhook("changed", self._track_local_changes,
                                    remote_info)
            local_info.event.unhook("changed", self._break_on_local_diverged,
                                    remote_info)
            local_info.event.unhook("flushed", self._break_on_local_flushed,
                                    remote_info)

            remote_info.event.unhook("changed", self._track_remote_changes,
                                     local_info)
            remote_info.event.unhook("changed", self._break_on_remote_diverged,
                                     weakref.ref(local_info))
            remote_info.event.unhook("flushed", self._break_on_remote_flushed,
                                     local_info)
            remote_info.event.unhook("removed", self._break_on_remote_removed,
                                     weakref.ref(local_info))

            if local_store is None:
                if not self.many or not remote_infos:
                    local_info.event.unhook("added", self._add_all, local_info)
                remote_info.event.unhook("added", self._add_all, local_info)
            else:
                flush_order = relation_data.get("flush_order")
                if flush_order is not None and remote_info in flush_order:
                    if self.on_remote:
                        local_store.remove_flush_order(local_info, remote_info)
                    else:
                        local_store.remove_flush_order(remote_info, local_info)
                    flush_order.remove(remote_info)

        if setting:
            if self.on_remote:
                remote_vars = remote_info.variables
                for remote_column in self.remote_key:
                    remote_vars[remote_column].set(None)
            else:
                local_vars = local_info.variables
                local_cols = self._get_local_columns(local_info.cls_info.cls)
                for local_column in local_cols:
                    local_vars[local_column].set(None)

    def _add_flush_order(self, local_info, remote_info, remote_first=False):
        """Tell the Store to flush objects in the specified order.

        We need to conditionally remove the flush order in unlink() only
        if we added it here.  Note that we can't just check if the Store
        has ordering on the (local, remote) pair, since it may have more
        than one request for ordering it, from different relations.

        @param local_info: The object info for the local object.
        @param remote_info: The object info for the remote object.
        @param remote_first: If True, remote_info will be flushed
                             before local_info.
        """
        local_store = Store.of(local_info)
        if local_store is not None:
            flush_order = local_info[self].setdefault("flush_order", set())
            if remote_info not in flush_order:
                flush_order.add(remote_info)
                if remote_first:
                    local_store.add_flush_order(remote_info, local_info)
                else:
                    local_store.add_flush_order(local_info, remote_info)

    def _track_local_changes(self, local_info, local_variable,
                             old_value, new_value, fromdb, remote_info):
        """Deliver changes in local to remote.

        This hook ensures that the remote object will keep track of
        changes done in the local object, either manually or at
        flushing time.
        """
        remote_column = self._get_remote_column(local_info.cls_info.cls,
                                                local_variable.column)
        if remote_column is not None:
            remote_info.variables[remote_column].set(new_value)
            self._add_flush_order(local_info, remote_info)

    def _track_remote_changes(self, remote_info, remote_variable,
                              old_value, new_value, fromdb, local_info):
        """Deliver changes in remote to local.

        This hook ensures that the local object will keep track of
        changes done in the remote object, either manually or at
        flushing time.
        """
        local_column = self._get_local_column(local_info.cls_info.cls,
                                              remote_variable.column)
        if local_column is not None:
            local_info.variables[local_column].set(new_value)
            self._add_flush_order(local_info, remote_info, remote_first=True)

    def _break_on_local_diverged(self, local_info, local_variable,
                                 old_value, new_value, fromdb, remote_info):
        """Break the remote/local relationship on diverging changes.

        This hook ensures that if the local object has an attribute
        changed by hand in a way that diverges from the remote object,
        it stops tracking changes.
        """
        remote_column = self._get_remote_column(local_info.cls_info.cls,
                                                local_variable.column)
        if remote_column is not None:
            variable = remote_info.variables[remote_column]
            if variable.get_lazy() is None and variable.get() != new_value:
                self.unlink(local_info, remote_info)

    def _break_on_remote_diverged(self, remote_info, remote_variable,
                                  old_value, new_value, fromdb, local_info_ref):
        """Break the remote/local relationship on diverging changes.

        This hook ensures that if the remote object has an attribute
        changed by hand in a way that diverges from the local object,
        the relationship is undone.
        """
        local_info = local_info_ref()
        if local_info is None:
            return
        local_column = self._get_local_column(local_info.cls_info.cls,
                                              remote_variable.column)
        if local_column is not None:
            local_value = local_info.variables[local_column].get()
            if local_value != new_value:
                self.unlink(local_info, remote_info)

    def _break_on_local_flushed(self, local_info, remote_info):
        """Break the remote/local relationship on flush."""
        self.unlink(local_info, remote_info)

    def _break_on_remote_flushed(self, remote_info, local_info):
        """Break the remote/local relationship on flush."""
        self.unlink(local_info, remote_info)

    def _break_on_remote_removed(self, remote_info, local_info_ref):
        """Break the remote relationship when the remote object is removed."""
        local_info = local_info_ref()
        if local_info is not None:
            self.unlink(local_info, remote_info)

    def _add_all(self, obj_info, local_info):
        store = Store.of(obj_info)
        store.add(local_info)
        local_info.event.unhook("added", self._add_all, local_info)

        def add(remote_info):
            remote_info.event.unhook("added", self._add_all, local_info)
            store.add(remote_info)
            self._add_flush_order(local_info, remote_info,
                                  remote_first=(not self.on_remote))

        if self.many:
            for remote_info in local_info[self]["remote"]:
                add(remote_info)
        else:
            add(get_obj_info(local_info[self]["remote"]))

    def _get_remote_columns(self, remote_cls):
        try:
            return self._remote_columns[remote_cls]
        except KeyError:
            columns = tuple(prop.__get__(None, remote_cls)
                            for prop in self.remote_key)
            self._remote_columns[remote_cls] = columns
            return columns

    def _get_local_columns(self, local_cls):
        try:
            return self._local_columns[local_cls]
        except KeyError:
            columns = tuple(prop.__get__(None, local_cls)
                            for prop in self.local_key)
            self._local_columns[local_cls] = columns
            return columns

    def _get_remote_column(self, local_cls, local_column):
        try:
            return self._l_to_r[local_cls].get(local_column)
        except KeyError:
            map = {}
            for local_prop, _remote_column in zip(self.local_key,
                                                  self.remote_key):
                map[local_prop.__get__(None, local_cls)] = _remote_column
            return self._l_to_r.setdefault(local_cls, map).get(local_column)

    def _get_local_column(self, local_cls, remote_column):
        try:
            return self._r_to_l[local_cls].get(remote_column)
        except KeyError:
            map = {}
            for local_prop, _remote_column in zip(self.local_key,
                                                   self.remote_key):
                map[_remote_column] = local_prop.__get__(None, local_cls)
            return self._r_to_l.setdefault(local_cls, map).get(remote_column)


class PropertyResolver(object):
    """Transform strings and pure properties (non-columns) into columns."""

    def __init__(self, reference, used_cls):
        self._reference = reference
        self._used_cls = used_cls

        self._registry = None
        self._namespace = None

    def resolve(self, properties):
        if not type(properties) is tuple:
            return (self.resolve_one(properties),)
        return tuple(self.resolve_one(property) for property in properties)

    def resolve_one(self, property):
        if type(property) is tuple:
            return self.resolve(property)
        elif isinstance(property, basestring):
            return self._resolve_string(property)
        elif not isinstance(property, Column):
            return _find_descriptor_obj(self._used_cls, property)
        return property

    def _resolve_string(self, property_path):
        if self._registry is None:
            try:
                registry = self._used_cls._storm_property_registry
            except AttributeError:
                raise RuntimeError("When using strings on references, "
                                   "classes involved must be subclasses "
                                   "of 'Storm'")
            cls = _find_descriptor_class(self._used_cls, self._reference)
            self._namespace = "%s.%s" % (cls.__module__, cls.__name__)

        return registry.get(property_path, self._namespace)


def _find_descriptor_class(used_cls, descr):
    for cls in used_cls.__mro__:
        for attr, _descr in cls.__dict__.iteritems():
            if _descr is descr:
                return cls
    raise RuntimeError("Reference used in an unknown class")

def _find_descriptor_obj(used_cls, descr):
    for cls in used_cls.__mro__:
        for attr, _descr in cls.__dict__.iteritems():
            if _descr is descr:
                return getattr(cls, attr)
    raise RuntimeError("Reference used in an unknown class")
