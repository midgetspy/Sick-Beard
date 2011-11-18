# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# generator.py - Generator with InProgress support
# -----------------------------------------------------------------------------
# $Id: generator.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'Generator', 'generator' ]

# kaa imports
from async import InProgress, inprogress
from thread import MAINTHREAD, threaded
from utils import wraps

class Generator(object):
    """
    Generator for InProgress objects
    """
    def __init__(self):
        self._waiting = None
        self._finished = []
        self._generator_exit = False
        self._populate = InProgress()

    def __inprogress__(self):
        """
        Wait until at least one item is produced or the generator
        finished before that happens.
        """
        return self._populate

    @threaded(MAINTHREAD)
    def send(self, result, exception=False):
        """
        Send a new value (producer)
        """
        delayed = [ InProgress(), result, False, exception ]
        if result is GeneratorExit:
            self._generator_exit = True
            delayed = None
        if not self._populate.finished:
            # First item
            self._delay = result
            self._waiting = delayed
            self._populate.finish(self)
            return
        ip, result, handled, exception = self._waiting
        if not handled:
            # InProgress not returned in __iter__, add it to the
            # finished objects
            self._finished.append(ip)
        self._waiting = delayed
        if exception:
            ip.throw(*result)
        else:
            ip.finish(result)

    def throw(self, type, value, tb):
        """
        Throw an error, this will stop the generator
        """
        self.send((type, value, tb), exception=True)
        self.send(GeneratorExit)
        return False

    def finish(self, result):
        """
        Finish the generator, the result will be ignored
        """
        self.send(GeneratorExit)

    def __iter__(self):
        """
        Iterate over the values (consumer)
        """
        while not self._generator_exit or self._waiting or self._finished:
            if not self._finished:
                # no finished items yet, return the waiting InProgress
                self._waiting[2] = True
                yield self._waiting[0]
            else:
                yield self._finished.pop(0)

# list of special handler
_generator_callbacks = {}

def generator(generic=False):
    """
    This decorator is used to construct asynchronous generators, to be used
    in combination with functions that return InProgress objects (such as
    those functions decorated with @:func:`kaa.coroutine` or @:func:`kaa.threaded`).

    :param generic: if True, a :class:`~kaa.Generator` object is passed as the 
                    first argument to the decorated function.  This can be used
                    for functions which have not been previously decoratored
                    with a supported decorator (such as @coroutine or @threaded).
    """
    def _decorator(func):
        callback = None
        if not generic:
            try:
                callback = _generator_callbacks[func.decorator]
            except KeyError:
                raise RuntimeError('Unsupported decorator: %s', func.decorator)
            except AttributeError:
                raise RuntimeError('Function %s does not support redecoration' % func)
            callback = func.redecorate()(callback)
            func = func.origfunc
        
        @wraps(func)
        def newfunc(*args, **kwargs):
            generator = Generator()
            if callback:
                ip = callback(generator, func, args, kwargs)
            else:
                ip = func(generator=generator, *args, **kwargs)
            try:
                ip.connect(generator.finish)
                ip.exception.connect(generator.throw)
            except AttributeError:
                raise ValueError('@kaa.generator decorated function (%s) must return InProgress' % func.func_name)
            return inprogress(generator)
        return newfunc

    return _decorator


def register(wrapper):
    """
    Register special handler for the generator
    """
    def decorator(func):
        _generator_callbacks[wrapper] = func
        return func
    return decorator

generator.register = register
