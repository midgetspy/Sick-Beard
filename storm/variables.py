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
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import cPickle as pickle
import re
try:
    import uuid
except ImportError:
    uuid = None

from storm.exceptions import NoneError
from storm import Undef, has_cextensions


__all__ = [
    "VariableFactory",
    "Variable",
    "LazyValue",
    "BoolVariable",
    "IntVariable",
    "FloatVariable",
    "DecimalVariable",
    "RawStrVariable",
    "UnicodeVariable",
    "DateTimeVariable",
    "DateVariable",
    "TimeVariable",
    "TimeDeltaVariable",
    "EnumVariable",
    "UUIDVariable",
    "PickleVariable",
    "ListVariable",
]


class LazyValue(object):
    """Marker to be used as a base class on lazily evaluated values."""
    __slots__ = ()


def raise_none_error(column):
    if not column:
        raise NoneError("None isn't acceptable as a value")
    else:
        from storm.expr import compile, CompileError
        name = column.name
        if column.table is not Undef:
            try:
                table = compile(column.table)
                name = "%s.%s" % (table, name)
            except CompileError:
                pass
        raise NoneError("None isn't acceptable as a value for %s" % name)


def VariableFactory(cls, **old_kwargs):
    """Build cls with kwargs of constructor updated by kwargs of call.

    This is really an implementation of partial/curry functions, and
    is replaced by 'partial' when 2.5+ is in use.
    """
    def variable_factory(**new_kwargs):
        kwargs = old_kwargs.copy()
        kwargs.update(new_kwargs)
        return cls(**kwargs)
    return variable_factory

try:
    from functools import partial as VariableFactory
except ImportError:
    pass


class Variable(object):
    """Basic representation of a database value in Python.

    @type column: L{storm.expr.Column}
    @ivar column: The column this variable represents.
    @type event: L{storm.event.EventSystem}
    @ivar event: The event system on which to broadcast events. If
        None, no events will be emitted.
    """

    _value = Undef
    _lazy_value = Undef
    _checkpoint_state = Undef
    _allow_none = True
    _validator = None
    _validator_object_factory = None
    _validator_attribute = None

    column = None
    event = None

    def __init__(self, value=Undef, value_factory=Undef, from_db=False,
                 allow_none=True, column=None, event=None, validator=None,
                 validator_object_factory=None, validator_attribute=None):
        """
        @param value: The initial value of this variable. The default
            behavior is for the value to stay undefined until it is
            set with L{set}.
        @param value_factory: If specified, this will immediately be
            called to get the initial value.
        @param from_db: A boolean value indicating where the initial
            value comes from, if C{value} or C{value_factory} are
            specified.
        @param allow_none: A boolean indicating whether None should be
            allowed to be set as the value of this variable.
        @param validator: Validation function called whenever trying to
            set the variable to a non-db value.  The function should
            look like validator(object, attr, value), where the first and
            second arguments are the result of validator_object_factory()
            (or None, if this parameter isn't provided) and the value of
            validator_attribute, respectively.  When called, the function
            should raise an error if the value is unacceptable, or return
            the value to be used in place of the original value otherwise.
        @type column: L{storm.expr.Column}
        @param column: The column that this variable represents. It's
            used for reporting better error messages.
        @type event: L{EventSystem}
        @param event: The event system to broadcast messages with. If
            not specified, then no events will be broadcast.
        """
        if not allow_none:
            self._allow_none = False
        if value is not Undef:
            self.set(value, from_db)
        elif value_factory is not Undef:
            self.set(value_factory(), from_db)
        if validator is not None:
            self._validator = validator
            self._validator_object_factory = validator_object_factory
            self._validator_attribute = validator_attribute
        self.column = column
        self.event = event

    def get_lazy(self, default=None):
        """Get the current L{LazyValue} without resolving its value.

        @param default: If no L{LazyValue} was previously specified,
            return this value. Defaults to None.
        """
        if self._lazy_value is Undef:
            return default
        return self._lazy_value

    def get(self, default=None, to_db=False):
        """Get the value, resolving it from a L{LazyValue} if necessary.

        If the current value is an instance of L{LazyValue}, then the
        C{resolve-lazy-value} event will be emitted, to give third
        parties the chance to resolve the lazy value to a real value.

        @param default: Returned if no value has been set.
        @param to_db: A boolean flag indicating whether this value is
            destined for the database.
        """
        if self._lazy_value is not Undef and self.event is not None:
            self.event.emit("resolve-lazy-value", self, self._lazy_value)
        value = self._value
        if value is Undef:
            return default
        if value is None:
            return None
        return self.parse_get(value, to_db)

    def set(self, value, from_db=False):
        """Set a new value.

        Generally this will be called when an attribute was set in
        Python, or data is being loaded from the database.

        If the value is different from the previous value (or it is a
        L{LazyValue}), then the C{changed} event will be emitted.

        @param value: The value to set. If this is an instance of
            L{LazyValue}, then later calls to L{get} will try to
            resolve the value.
        @param from_db: A boolean indicating whether this value has
            come from the database.
        """
        # FASTPATH This method is part of the fast path.  Be careful when
        #          changing it (try to profile any changes).

        if isinstance(value, LazyValue):
            self._lazy_value = value
            self._checkpoint_state = new_value = Undef
        else:
            if not from_db and self._validator is not None:
                # We use a factory rather than the object itself to prevent
                # the cycle object => obj_info => variable => object
                value = self._validator(self._validator_object_factory and
                                        self._validator_object_factory(),
                                        self._validator_attribute, value)
            self._lazy_value = Undef
            if value is None:
                if self._allow_none is False:
                    raise_none_error(self.column)
                new_value = None
            else:
                new_value = self.parse_set(value, from_db)
                if from_db:
                    # Prepare it for being used by the hook below.
                    value = self.parse_get(new_value, False)
        old_value = self._value
        self._value = new_value
        if (self.event is not None and
            (self._lazy_value is not Undef or new_value != old_value)):
            if old_value is not None and old_value is not Undef:
                old_value = self.parse_get(old_value, False)
            self.event.emit("changed", self, old_value, value, from_db)

    def delete(self):
        """Delete the internal value.

        If there was a value set, then emit the C{changed} event.
        """
        old_value = self._value
        if old_value is not Undef:
            self._value = Undef
            if self.event is not None:
                if old_value is not None and old_value is not Undef:
                    old_value = self.parse_get(old_value, False)
                self.event.emit("changed", self, old_value, Undef, False)

    def is_defined(self):
        """Check whether there is currently a value.

        @return: boolean indicating whether there is currently a value
            for this variable. Note that if a L{LazyValue} was
            previously set, this returns False; it only returns True if
            there is currently a real value set.
        """
        return self._value is not Undef

    def has_changed(self):
        """Check whether the value has changed.

        @return: boolean indicating whether the value has changed
            since the last call to L{checkpoint}.
        """
        return (self._lazy_value is not Undef or
                self.get_state() != self._checkpoint_state)

    def get_state(self):
        """Get the internal state of this object.

        @return: A value which can later be passed to L{set_state}.
        """
        return (self._lazy_value, self._value)

    def set_state(self, state):
        """Set the internal state of this object.

        @param state: A result from a previous call to
            L{get_state}. The internal state of this variable will be set
            to the state of the variable which get_state was called on.
        """
        self._lazy_value, self._value = state

    def checkpoint(self):
        """"Checkpoint" the internal state.

        See L{has_changed}.
        """
        self._checkpoint_state = self.get_state()

    def copy(self):
        """Make a new copy of this Variable with the same internal state."""
        variable = self.__class__.__new__(self.__class__)
        variable.set_state(self.get_state())
        return variable

    def parse_get(self, value, to_db):
        """Convert the internal value to an external value.

        Get a representation of this value either for Python or for
        the database. This method is only intended to be overridden
        in subclasses, not called from external code.

        @param value: The value to be converted.
        @param to_db: Whether or not this value is destined for the
            database.
        """
        return value

    def parse_set(self, value, from_db):
        """Convert an external value to an internal value.

        A value is being set either from Python code or from the
        database. Parse it into its internal representation.  This
        method is only intended to be overridden in subclasses, not
        called from external code.

        @param value: The value, either from Python code setting an
            attribute or from a column in a database.
        @param from_db: A boolean flag indicating whether this value
            is from the database.
        """
        return value


if has_cextensions:
    from storm.cextensions import Variable


class BoolVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if not isinstance(value, (int, long, float, Decimal)):
            raise TypeError("Expected bool, found %r: %r"
                            % (type(value), value))
        return bool(value)


class IntVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if not isinstance(value, (int, long, float, Decimal)):
            raise TypeError("Expected int, found %r: %r"
                            % (type(value), value))
        return int(value)


class FloatVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if not isinstance(value, (int, long, float, Decimal)):
            raise TypeError("Expected float, found %r: %r"
                            % (type(value), value))
        return float(value)


class DecimalVariable(Variable):
    __slots__ = ()

    @staticmethod
    def parse_set(value, from_db):
        if (from_db and isinstance(value, basestring) or
            isinstance(value, (int, long))):
            value = Decimal(value)
        elif not isinstance(value, Decimal):
            raise TypeError("Expected Decimal, found %r: %r"
                            % (type(value), value))
        return value

    @staticmethod
    def parse_get(value, to_db):
        if to_db:
            return str(value)
        return value


class RawStrVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if isinstance(value, buffer):
            value = str(value)
        elif not isinstance(value, str):
            raise TypeError("Expected str, found %r: %r"
                            % (type(value), value))
        return value


class UnicodeVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if not isinstance(value, unicode):
            raise TypeError("Expected unicode, found %r: %r"
                            % (type(value), value))
        return value


class DateTimeVariable(Variable):
    __slots__ = ("_tzinfo",)

    def __init__(self, *args, **kwargs):
        self._tzinfo = kwargs.pop("tzinfo", None)
        super(DateTimeVariable, self).__init__(*args, **kwargs)

    def parse_set(self, value, from_db):
        if from_db:
            if isinstance(value, datetime):
                pass
            elif isinstance(value, (str, unicode)):
                if " " not in value:
                    raise ValueError("Unknown date/time format: %r" % value)
                date_str, time_str = value.split(" ")
                value = datetime(*(_parse_date(date_str) +
                                   _parse_time(time_str)))
            else:
                raise TypeError("Expected datetime, found %s" % repr(value))
            if self._tzinfo is not None:
                if value.tzinfo is None:
                    value = value.replace(tzinfo=self._tzinfo)
                else:
                    value = value.astimezone(self._tzinfo)
        else:
            if type(value) in (int, long, float):
                value = datetime.utcfromtimestamp(value)
            elif not isinstance(value, datetime):
                raise TypeError("Expected datetime, found %s" % repr(value))
            if self._tzinfo is not None:
                value = value.astimezone(self._tzinfo)
        return value


class DateVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if from_db:
            if value is None:
                return None
            if isinstance(value, date):
                return value
            if not isinstance(value, (str, unicode)):
                raise TypeError("Expected date, found %s" % repr(value))
            if " " in value:
                value, time_str = value.split(" ")
            return date(*_parse_date(value))
        else:
            if isinstance(value, datetime):
                return value.date()
            if not isinstance(value, date):
                raise TypeError("Expected date, found %s" % repr(value))
            return value


class TimeVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if from_db:
            # XXX Can None ever get here, considering that set() checks for it?
            if value is None:
                return None
            if isinstance(value, time):
                return value
            if not isinstance(value, (str, unicode)):
                raise TypeError("Expected time, found %s" % repr(value))
            if " " in value:
                date_str, value = value.split(" ")
            return time(*_parse_time(value))
        else:
            if isinstance(value, datetime):
                return value.time()
            if not isinstance(value, time):
                raise TypeError("Expected time, found %s" % repr(value))
            return value


class TimeDeltaVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if from_db:
            # XXX Can None ever get here, considering that set() checks for it?
            if value is None:
                return None
            if isinstance(value, timedelta):
                return value
            if not isinstance(value, (str, unicode)):
                raise TypeError("Expected timedelta, found %s" % repr(value))
            return _parse_interval(value)
        else:
            if not isinstance(value, timedelta):
                raise TypeError("Expected timedelta, found %s" % repr(value))
            return value


class UUIDVariable(Variable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        assert uuid is not None, "The uuid module was not found."
        if from_db and isinstance(value, basestring):
            value = uuid.UUID(value)
        elif not isinstance(value, uuid.UUID):
            raise TypeError("Expected UUID, found %r: %r"
                            % (type(value), value))
        return value

    def parse_get(self, value, to_db):
        if to_db:
            return str(value)
        return value


class EnumVariable(Variable):
    __slots__ = ("_get_map", "_set_map")

    def __init__(self, get_map, set_map, *args, **kwargs):
        self._get_map = get_map
        self._set_map = set_map
        Variable.__init__(self, *args, **kwargs)

    def parse_set(self, value, from_db):
        if from_db:
            return value
        try:
            return self._set_map[value]
        except KeyError:
            raise ValueError("Invalid enum value: %s" % repr(value))

    def parse_get(self, value, to_db):
        if to_db:
            return value
        try:
            return self._get_map[value]
        except KeyError:
            raise ValueError("Invalid enum value: %s" % repr(value))


class MutableValueVariable(Variable):
    """
    A variable which contains a reference to mutable content. For this kind
    of variable, we can't simply detect when a modification has been made, so
    we have to synchronize the content of the variable when the store is
    flushing current objects, to check if the state has changed.
    """
    __slots__ = ("_event_system")

    def __init__(self, *args, **kwargs):
        self._event_system = None
        Variable.__init__(self, *args, **kwargs)
        if self.event is not None:
            self.event.hook("start-tracking-changes", self._start_tracking)
            self.event.hook("object-deleted", self._detect_changes_and_stop)

    def _start_tracking(self, obj_info, event_system):
        self._event_system = event_system
        self.event.hook("stop-tracking-changes", self._stop_tracking)

    def _stop_tracking(self, obj_info, event_system):
        event_system.unhook("flush", self._detect_changes)
        self._event_system = None

    def _detect_changes(self, obj_info):
        if (self._checkpoint_state is not Undef and
            self.get_state() != self._checkpoint_state):
            self.event.emit("changed", self, None, self._value, False)
    
    def _detect_changes_and_stop(self, obj_info):
        self._detect_changes(obj_info)
        if self._event_system is not None:
            self._stop_tracking(obj_info, self._event_system)

    def get(self, default=None, to_db=False):
        if self._event_system is not None:
            self._event_system.hook("flush", self._detect_changes)
        return super(MutableValueVariable, self).get(default, to_db)

    def set(self, value, from_db=False):
        if self._event_system is not None:
            if isinstance(value, LazyValue):
                self._event_system.unhook("flush", self._detect_changes)
            else:
                self._event_system.hook("flush", self._detect_changes)
        super(MutableValueVariable, self).set(value, from_db)


class PickleVariable(MutableValueVariable):
    __slots__ = ()

    def parse_set(self, value, from_db):
        if from_db:
            if isinstance(value, buffer):
                value = str(value)
            return pickle.loads(value)
        else:
            return value

    def parse_get(self, value, to_db):
        if to_db:
            return pickle.dumps(value, -1)
        else:
            return value

    def get_state(self):
        return (self._lazy_value, pickle.dumps(self._value, -1))

    def set_state(self, state):
        self._lazy_value = state[0]
        self._value = pickle.loads(state[1])


class ListVariable(MutableValueVariable):
    __slots__ = ("_item_factory",)

    def __init__(self, item_factory, *args, **kwargs):
        self._item_factory = item_factory
        MutableValueVariable.__init__(self, *args, **kwargs)

    def parse_set(self, value, from_db):
        if from_db:
            item_factory = self._item_factory
            return [item_factory(value=val, from_db=from_db).get()
                    for val in value]
        else:
            return value

    def parse_get(self, value, to_db):
        if to_db:
            item_factory = self._item_factory
            return [item_factory(value=val, from_db=False) for val in value]
        else:
            return value

    def get_state(self):
        return (self._lazy_value, pickle.dumps(self._value, -1))

    def set_state(self, state):
        self._lazy_value = state[0]
        self._value = pickle.loads(state[1])


def _parse_time(time_str):
    # TODO Add support for timezones.
    colons = time_str.count(":")
    if not 1 <= colons <= 2:
        raise ValueError("Unknown time format: %r" % time_str)
    if colons == 2:
        hour, minute, second = time_str.split(":")
    else:
        hour, minute = time_str.split(":")
        second = "0"
    if "." in second:
        second, microsecond = second.split(".")
        second = int(second)
        microsecond = int(int(microsecond) * 10 ** (6 - len(microsecond)))
        return int(hour), int(minute), second, microsecond
    return int(hour), int(minute), int(second), 0

def _parse_date(date_str):
    if "-" not in date_str:
        raise ValueError("Unknown date format: %r" % date_str)
    year, month, day = date_str.split("-")
    return int(year), int(month), int(day)


def _parse_interval_table():
    table = {}
    for units, delta in (
        ("d day days", timedelta),
        ("h hour hours", lambda x: timedelta(hours=x)),
        ("m min minute minutes", lambda x: timedelta(minutes=x)),
        ("s sec second seconds", lambda x: timedelta(seconds=x)),
        ("ms millisecond milliseconds", lambda x: timedelta(milliseconds=x)),
        ("microsecond microseconds", lambda x: timedelta(microseconds=x))
        ):
        for unit in units.split():
            table[unit] = delta
    return table

_parse_interval_table = _parse_interval_table()

_parse_interval_re = re.compile(r"[\s,]*"
                                r"([-+]?(?:\d\d?:\d\d?(?::\d\d?)?(?:\.\d+)?"
                                r"|\d+(?:\.\d+)?))"
                                r"[\s,]*")

def _parse_interval(interval):
    result = timedelta(0)
    value = None
    for token in _parse_interval_re.split(interval):
        if not token:
            pass
        elif ":" in token:
            if value is not None:
                result += timedelta(days=value)
                value = None
            h, m, s, ms = _parse_time(token)
            result += timedelta(hours=h, minutes=m, seconds=s, microseconds=ms)
        elif value is None:
            try:
                value = float(token)
            except ValueError:
                raise ValueError("Expected an interval value rather than "
                                 "%r in interval %r" % (token, interval))
        else:
            unit = _parse_interval_table.get(token)
            if unit is None:
                raise ValueError("Unsupported interval unit %r in interval %r"
                                 % (token, interval))
            result += unit(value)
            value = None
    if value is not None:
        result += timedelta(seconds=value)
    return result
