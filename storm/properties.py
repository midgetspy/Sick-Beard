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
from bisect import insort_left, bisect_left
import weakref
import sys

from storm.exceptions import PropertyPathError
from storm.info import get_obj_info, get_cls_info
from storm.expr import Column, Undef
from storm.variables import (
    Variable, VariableFactory, BoolVariable, IntVariable, FloatVariable,
    DecimalVariable, RawStrVariable, UnicodeVariable, DateTimeVariable,
    DateVariable, TimeVariable, TimeDeltaVariable, UUIDVariable,
    PickleVariable, ListVariable, EnumVariable)



__all__ = ["Property", "SimpleProperty",
           "Bool", "Int", "Float", "Decimal", "RawStr", "Unicode",
           "DateTime", "Date", "Time", "TimeDelta", "UUID", "Enum",
           "Pickle", "List", "PropertyRegistry"]


class Property(object):

    def __init__(self, name=None, primary=False,
                 variable_class=Variable, variable_kwargs={}):
        self._name = name
        self._primary = primary
        self._variable_class = variable_class
        self._variable_kwargs = variable_kwargs

    def __get__(self, obj, cls=None):
        if obj is None:
            return self._get_column(cls)
        obj_info = get_obj_info(obj)
        if cls is None:
            # Don't get obj.__class__ because we don't trust it
            # (might be proxied or whatever).
            cls = obj_info.cls_info.cls
        column = self._get_column(cls)
        return obj_info.variables[column].get()

    def __set__(self, obj, value):
        obj_info = get_obj_info(obj)
        # Don't get obj.__class__ because we don't trust it
        # (might be proxied or whatever).
        column = self._get_column(obj_info.cls_info.cls)
        obj_info.variables[column].set(value)

    def __delete__(self, obj):
        obj_info = get_obj_info(obj)
        # Don't get obj.__class__ because we don't trust it
        # (might be proxied or whatever).
        column = self._get_column(obj_info.cls_info.cls)
        obj_info.variables[column].delete()

    def _detect_attr_name(self, used_cls):
        self_id = id(self)
        for cls in used_cls.__mro__:
            for attr, prop in cls.__dict__.items():
                if id(prop) == self_id:
                    return attr
        raise RuntimeError("Property used in an unknown class")

    def _get_column(self, cls):
        # Cache per-class column values in the class itself, to avoid
        # holding a strong reference to it here, and thus rendering
        # classes uncollectable in certain situations (e.g. subclasses
        # where the property is stored in the base).
        try:
            # Use class dictionary explicitly to get sensible
            # results on subclasses.
            column = cls.__dict__["_storm_columns"].get(self)
        except KeyError:
            cls._storm_columns = {}
            column = None
        if column is None:
            attr = self._detect_attr_name(cls)
            if self._name is None:
                name = attr
            else:
                name = self._name
            column = PropertyColumn(self, cls, attr, name, self._primary,
                                    self._variable_class,
                                    self._variable_kwargs)
            cls._storm_columns[self] = column
        return column


class PropertyColumn(Column):

    def __init__(self, prop, cls, attr, name, primary,
                 variable_class, variable_kwargs):
        Column.__init__(self, name, cls, primary,
                        VariableFactory(variable_class, column=self,
                                        validator_attribute=attr,
                                        **variable_kwargs))

        self.cls = cls # Used by references

        # Copy attributes from the property to avoid one additional
        # function call on each access.
        for attr in ["__get__", "__set__", "__delete__"]:
            setattr(self, attr, getattr(prop, attr))


class SimpleProperty(Property):

    variable_class = None

    def __init__(self, name=None, primary=False, **kwargs):
        kwargs["value"] = kwargs.pop("default", Undef)
        kwargs["value_factory"] = kwargs.pop("default_factory", Undef)
        Property.__init__(self, name, primary, self.variable_class, kwargs)


class Bool(SimpleProperty):
    variable_class = BoolVariable
 
class Int(SimpleProperty):
    variable_class = IntVariable

class Float(SimpleProperty):
    variable_class = FloatVariable

class Decimal(SimpleProperty):
    variable_class = DecimalVariable

class RawStr(SimpleProperty):
    variable_class = RawStrVariable

# OBSOLETE RawStr was Chars in 0.9. This will die soon.
Chars = RawStr

class Unicode(SimpleProperty):
    variable_class = UnicodeVariable

class DateTime(SimpleProperty):
    variable_class = DateTimeVariable

class Date(SimpleProperty):
    variable_class = DateVariable

class Time(SimpleProperty):
    variable_class = TimeVariable

class TimeDelta(SimpleProperty):
    variable_class = TimeDeltaVariable

class UUID(SimpleProperty):
    variable_class = UUIDVariable

class Pickle(SimpleProperty):
    variable_class = PickleVariable


class List(SimpleProperty):
    variable_class = ListVariable

    def __init__(self, name=None, **kwargs):
        if "default" in kwargs:
            raise ValueError("'default' not allowed for List. "
                             "Use 'default_factory' instead.")
        type = kwargs.pop("type", None)
        if type is None:
            type = Property()
        kwargs["item_factory"] = VariableFactory(type._variable_class,
                                                 **type._variable_kwargs)
        SimpleProperty.__init__(self, name, **kwargs)


class Enum(SimpleProperty):
    """Enumeration property, allowing used values to differ from stored ones.

    For instance::

        class Class(Storm):
            prop = Enum(map={"one": 1, "two": 2})

        obj.prop = "one"
        assert obj.prop == "one"

        obj.prop = 1 # Raises error.

    Another example::

        class Class(Storm):
            prop = Enum(map={"one": 1, "two": 2}, set_map={"um": 1})

        obj.prop = "um"
        assert obj.prop is "one"

        obj.prop = "one" # Raises error.
    """
    variable_class = EnumVariable

    def __init__(self, name=None, primary=False, **kwargs):
        set_map = dict(kwargs.pop("map"))
        get_map = dict((value, key) for key, value in set_map.items())
        if "set_map" in kwargs:
            set_map = dict(kwargs.pop("set_map"))

        kwargs["get_map"] = get_map
        kwargs["set_map"] = set_map
        SimpleProperty.__init__(self, name, primary, **kwargs)


class PropertyRegistry(object):
    """
    An object which remembers the Storm properties specified on
    classes, and is able to translate names to these properties.
    """
    def __init__(self):
        self._properties = []

    def get(self, name, namespace=None):
        """Translate a property name path to the actual property.

        This method accepts a property name like C{"id"} or C{"Class.id"}
        or C{"module.path.Class.id"}, and tries to find a unique
        class/property with the given name.

        When the C{namespace} argument is given, the registry will be
        able to disambiguate names by choosing the one that is closer
        to the given namespace.  For instance C{get("Class.id", "a.b.c")}
        will choose C{a.Class.id} rather than C{d.Class.id}.
        """
        key = ".".join(reversed(name.split(".")))+"."
        i = bisect_left(self._properties, (key,))
        l = len(self._properties)
        best_props = []
        if namespace is None:
            while i < l and self._properties[i][0].startswith(key):
                path, prop_ref = self._properties[i]
                prop = prop_ref()
                if prop is not None:
                    best_props.append((path, prop))
                i += 1
        else:
            namespace_parts = ("." + namespace).split(".")
            best_path_info = (0, sys.maxint)
            while i < l and self._properties[i][0].startswith(key):
                path, prop_ref = self._properties[i]
                prop = prop_ref()
                if prop is None:
                    i += 1
                    continue
                path_parts = path.split(".")
                path_parts.reverse()
                common_prefix = 0
                for part, ns_part in zip(path_parts, namespace_parts):
                    if part == ns_part:
                        common_prefix += 1
                    else:
                        break
                path_info = (-common_prefix, len(path_parts)-common_prefix)
                if path_info < best_path_info:
                    best_path_info = path_info
                    best_props = [(path, prop)]
                elif path_info == best_path_info:
                    best_props.append((path, prop))
                i += 1
        if not best_props:
            raise PropertyPathError("Path '%s' matches no known property."
                                    % name)
        elif len(best_props) > 1:
            paths = [".".join(reversed(path.split(".")[:-1]))
                     for path, prop in best_props]
            raise PropertyPathError("Path '%s' matches multiple "
                                    "properties: %s" %
                                    (name, ", ".join(paths)))
        return best_props[0][1]

    def add_class(self, cls):
        """Register properties of C{cls} so that they may be found by C{get()}.
        """
        suffix = cls.__module__.split(".")
        suffix.append(cls.__name__)
        suffix.reverse()
        suffix = ".%s." % ".".join(suffix)
        cls_info = get_cls_info(cls)
        for attr in cls_info.attributes:
            prop = cls_info.attributes[attr]
            prop_ref = weakref.KeyedRef(prop, self._remove, None)
            pair = (attr+suffix, prop_ref)
            prop_ref.key = pair
            insort_left(self._properties, pair)

    def add_property(self, cls, prop, attr_name):
        """Register property of C{cls} so that it may be found by C{get()}.
        """
        suffix = cls.__module__.split(".")
        suffix.append(cls.__name__)
        suffix.reverse()
        suffix = ".%s." % ".".join(suffix)
        prop_ref = weakref.KeyedRef(prop, self._remove, None)
        pair = (attr_name+suffix, prop_ref)
        prop_ref.key = pair
        insort_left(self._properties, pair)

    def clear(self):
        """Clean up all properties in the registry.

        Used by tests.
        """
        del self._properties[:]

    def _remove(self, ref):
        self._properties.remove(ref.key)


class PropertyPublisherMeta(type):
    """A metaclass that associates subclasses with Storm L{PropertyRegistry}s.
    """

    def __init__(self, name, bases, dict):
        if not hasattr(self, "_storm_property_registry"):
            self._storm_property_registry = PropertyRegistry()
        elif hasattr(self, "__storm_table__"):
            self._storm_property_registry.add_class(self)
