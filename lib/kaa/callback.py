# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# callback.py - Callback classes
# -----------------------------------------------------------------------------
# $Id: callback.py 4072 2009-05-25 17:33:32Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2005-2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'Callback', 'WeakCallback', 'CallbackError' ]

# Python imports
import _weakref
import types
import logging
import atexit

# Kaa imports
from utils import property

# get logging object
log = logging.getLogger('base')

# Variable that is set to True (via atexit callback) when python interpreter
# is in the process of shutting down.  If we're interested if the interpreter
# is shutting down, we don't want to test that this variable is True, but
# rather that it is not False, because as it is prefixed with an underscore,
# the interpreter might already have deleted this variable in which case it
# is None.
_python_shutting_down = False


def weakref_data(data, destroy_cb = None):
    if type(data) in (str, int, long, types.NoneType, types.FunctionType):
        # Naive optimization for common immutable cases.
        return data
    elif type(data) == types.MethodType:
        cb = WeakCallback(data)
        if destroy_cb:
            cb.weakref_destroyed_cb = destroy_cb
            cb.ignore_caller_args = True
        return cb
    elif type(data) in (list, tuple):
        d = []
        for item in data:
            d.append(weakref_data(item, destroy_cb))
        if type(data) == tuple:
            d = tuple(d)
        return d
    elif type(data) == dict:
        d = {}
        for key, val in data.items():
            d[weakref_data(key)] = weakref_data(val, destroy_cb)
        return d
    else:
        try:
            if destroy_cb:
                return _weakref.ref(data, destroy_cb)
            return _weakref.ref(data)
        except TypeError:
            pass

    return data

def unweakref_data(data):
    if type(data) in (str, int, long, types.NoneType):
        # Naive optimization for common immutable cases.
        return data
    elif type(data) == _weakref.ReferenceType:
        return data()
    elif type(data) == WeakCallback:
        return data._get_callback()
    elif type(data) in (list, tuple):
        d = []
        for item in data:
            d.append(unweakref_data(item))
        if type(data) == tuple:
            d = tuple(d)
        return d
    elif type(data) == dict:
        d = {}
        for key, val in data.items():
            d[unweakref_data(key)] = unweakref_data(val)
        return d
    else:
        return data


class CallbackError(Exception):
    pass


class Callback(object):
    """
    Wraps an existing callable, binding to it the given args and kwargs.

    When the Callback object is invoked, the arguments passed on invocation
    are combined with the arguments specified at construction time and the
    underlying callback function is invoked with those arguments.
    """
    def __init__(self, callback, *args, **kwargs):
        """
        :param callback: callable function or object
        :param args: arguments for the callback
        :param kwargs: keyword arguments for the callback
        """
        super(Callback, self).__init__()
        assert(callable(callback))
        self._callback = callback
        self._callback_name = str(callback)
        self._args = args
        self._kwargs = kwargs
        self._ignore_caller_args = False
        self._user_args_first = False


    @property
    def ignore_caller_args(self):
        """
        If True, any arguments passed when invoking the Callback object are not
        passed to the underlying callable.

        Default value is False, so all arguments are passed to the callable.
        """
        return self._ignore_caller_args

    @ignore_caller_args.setter
    def ignore_caller_args(self, value):
        self._ignore_caller_args = value


    @property
    def user_args_first(self):
        """
        If True, any arguments passed upon invocation of the Callback object take
        precedence over those arguments passed to the constructor ("user args").
        e.g. ``callback(constructor_args..., invocation_args...)``

        Default value is False, so invocation arguments take precedence over user
        arguments. e.g. ``callback(invocation_args..., constructor_args...)``

        "A takes precedence over B" means that non-keyword arguments are passed
        in order of A + B, and keyword arguments from A override same-named keyword
        arguments from B.
        """
        return self._user_args_first

    @user_args_first.setter
    def user_args_first(self, value):
        self._user_args_first = value


    def _get_user_args(self):
        """
        Return the arguments provided by the user on __init__.
        """
        return self._args, self._kwargs


    def _get_callback(self):
        return self._callback


    def _merge_args(self, args, kwargs):
        user_args, user_kwargs = self._get_user_args()
        if self.ignore_caller_args:
            cb_args, cb_kwargs = user_args, user_kwargs
        else:
            if self.user_args_first:
                cb_args, cb_kwargs = user_args + args, kwargs.copy()
                cb_kwargs.update(user_kwargs)
            else:
                cb_args, cb_kwargs = args + user_args, user_kwargs.copy()
                cb_kwargs.update(kwargs)

        return cb_args, cb_kwargs


    def __call__(self, *args, **kwargs):
        """
        Invoke the callback function passed upon construction.

        The arguments passed here take precedence over constructor arguments
        if the :attr:`~kaa.Callback.user_args_first` property is False (default).
        The underlying callback's return value is returned.
        """
        cb = self._get_callback()
        cb_args, cb_kwargs = self._merge_args(args, kwargs)
        if not cb:
            raise CallbackError('The callback (%s) has become invalid.' % self._callback_name)

        self._entered = True
        result = cb(*cb_args, **cb_kwargs)
        self._entered = False
        return result


    def __repr__(self):
        """
        Convert to string for debug.
        """
        return '<%s for %s>' % (self.__class__.__name__, self._callback)


    def __deepcopy__(self, memo):
        """
        Disable deepcopying because deepcopy can't deal with callables.
        """
        return None

    def __eq__(self, func):
        """
        Compares the given function with the callback function we're wrapping.
        """
        return id(self) == id(func) or self._get_callback() == func


class WeakCallback(Callback):
    """
    Weak variant of the Callback class.  Only weak references are held for
    non-intrinsic types (i.e. any user-defined object).

    If the callable is a method, only a weak reference is kept to the instance
    to which that method belongs, and only weak references are kept to any of
    the arguments and keyword arguments.

    This also works recursively, so if there are nested data structures, for example 
    ``kwarg=[1, [2, [3, my_object]]]``, only a weak reference is held for my_object.
    """

    def __init__(self, callback, *args, **kwargs):
        super(WeakCallback, self).__init__(callback, *args, **kwargs)
        if type(callback) == types.MethodType:
            # For methods
            self._instance = _weakref.ref(callback.im_self, self._weakref_destroyed)
            self._callback = callback.im_func.func_name
        else:
            self._instance = None
            # Don't weakref lambdas.
            if not hasattr(callback, 'func_name') or callback.func_name != '<lambda>':
                self._callback = _weakref.ref(callback, self._weakref_destroyed)

        self._args = weakref_data(args, self._weakref_destroyed)
        self._kwargs = weakref_data(kwargs, self._weakref_destroyed)
        self._weakref_destroyed_user_cb = None


    def __repr__(self):
        if self._instance and self._instance():
            name = "method %s of %s" % (self._callback, self._instance())
        else:
            name = self._callback
        return '<%s for %s>' % (self.__class__.__name__, name)

    def _get_callback(self):
        if self._instance:
            if self._instance() != None:
                return getattr(self._instance(), self._callback)
        elif isinstance(self._callback, _weakref.ReferenceType):
            return self._callback()
        else:
            return self._callback


    def _get_user_args(self):
        return unweakref_data(self._args), unweakref_data(self._kwargs)


    def __call__(self, *args, **kwargs):
        if _python_shutting_down != False:
            # Shutdown
            return False

        return super(WeakCallback, self).__call__(*args, **kwargs)


    @property
    def weakref_destroyed_cb(self):
        """
        A callback that's invoked when any of the weak references held (either
        for the callable or any of the arguments passed on the constructor)
        become dead.

        When this happens, the Callback is invalid and any attempt to invoke
        it will raise a kaa.CallbackError.

        The callback is passed the weakref object (which is probably dead).
        If the callback requires additional arguments, they can be encapsulated
        in a :class:`kaa.Callback` object.
        """
        return self._weakref_destroyed_user_cb

    @weakref_destroyed_cb.setter
    def weakref_destroyed_cb(self, callback):
        if not callable(callback):
            raise ValueError('Value must be a callable')
        self._weakref_destroyed_user_cb = callback



    def _weakref_destroyed(self, object):
        if _python_shutting_down != False:
            # Shutdown
            return
        try:
            if self._weakref_destroyed_user_cb:
                return self._weakref_destroyed_user_cb(object)
        except Exception:
            log.exception("Exception raised during weakref destroyed callback")
        finally:
            # One of the weak refs has died, consider this WeakCallback invalid.
            self._instance = self._callback = None



def _shutdown_weakref_destroyed():
    global _python_shutting_down
    _python_shutting_down = True

atexit.register(_shutdown_weakref_destroyed)
