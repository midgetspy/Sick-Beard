# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# weakref.py - weak reference
# -----------------------------------------------------------------------------
# $Id: weakref.py 4070 2009-05-25 15:32:31Z tack $
#
# This file contains a wrapper for weakref that the weak reference can
# be used the same way the real object would be used.
#
# -----------------------------------------------------------------------------
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'weakref' ]

# python imports
from _weakref import ref


class NoneProxy(object):
    def __call__(self):
        return None

class weakref(object):
    """
    This class represents a weak reference based on the python
    module weakref. The difference between weakref.ref and this class
    is that you can access the ref without calling it first.
    E.g.: foo = weak(bar) and bar has the attribute x. With a normal
    weakref.ref you need to call foo().x to get, this class makes it
    possible to just use foo.x.

    All functions are passed to the real object behind the weakref. To
    check if the weakref is alive or not, you can compare the object with
    None. Do not use a simple if, because an object still alive can also
    be False (e.g. an empty list).
    """
    def __new__(cls, object):
        # Make an instance of callable weakref iff the object is callable.
        # This way callable(weakref) == False if the underlying object isn't
        # callable.
        if callable(object):
            cls = _callable_weakref
        return super(weakref, weakref).__new__(cls, object)

    def __init__(self, object):
        if object is not None:
            if type(object) == weakref:
                self._ref = object._ref
            else:
                self._ref = ref(object)
        else:
            self._ref = NoneProxy()

    def __getattribute__(self, attr):
        if attr == "__class__":
            return self._ref().__class__
        if attr == "_ref":
            return object.__getattribute__(self, attr)
        return getattr(self._ref(), attr)

    def __setattr__(self, attr, value):
        if attr == "_ref":
            return object.__setattr__(self, attr, value)
        return setattr(self._ref(), attr, value)

    def __delattr__(self, attr):
        return delattr(self._ref(), attr)

    def __getitem__(self, key):
        return self._ref()[key]

    def __delitem__(self, key):
        del self._ref()[key]

    def __setitem__(self, key, value):
        self._ref()[key] = value

    def __nonzero__(self):
        if self._ref():
            return 1
        else:
            return 0

    def __cmp__(self, other):
        if type(other) == weakref:
            other = other._ref()
        return cmp(self._ref(), other)

    def __str__(self):
        return "<weakref proxy; %s>" % str(self._ref())

    def __deepcopy__(self, memo):
        return weakref(self._ref())


class _callable_weakref(weakref):
    def __new__(cls, object):
        return super(weakref, weakref).__new__(cls)

    def __call__(self, *args, **kwargs):
        return self._ref()(*args, **kwargs)
