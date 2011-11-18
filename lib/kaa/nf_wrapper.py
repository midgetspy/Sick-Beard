# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# nf_wrapper.py - Wrapper to notifier calls to delay the real import
# -----------------------------------------------------------------------------
# $Id: nf_wrapper.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry, et al.
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

# Python imports
import logging
import sys
import atexit

# notifier import
from callback import Callback, WeakCallback, CallbackError
from signals import Signal
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


class NotifierCallback(Callback):

    def __init__(self, callback, *args, **kwargs):
        super(NotifierCallback, self).__init__(callback, *args, **kwargs)
        self._id = None

        self.signals = {
            "exception": Signal(),
            "unregistered": Signal()
        }


    @property
    def active(self):
        """
        True if the callback is registered with the notifier.
        """
        # callback is active if id is not None and python is not shutting down
        # if python is in shutdown, notifier unregister could crash
        return self._id != None and _python_shutting_down == False


    def unregister(self):
        # Unregister callback with notifier.  Must be implemented by subclasses.
        self.signals["unregistered"].emit()
        self._id = None


    def __call__(self, *args, **kwargs):
        if not self._get_callback():
            if self.active:
                self.unregister()
            return False

        try:
            ret = super(NotifierCallback, self).__call__(*args, **kwargs)
        except CallbackError:
            # A WeakCallback that's no longer valid.  Unregister.
            ret = False
        except Exception:
            # If there are exception handlers for this notifier callback, we
            # catch the exception and pass it to the handler, giving it the
            # opportunity to abort the unregistering.  If no handlers are
            # attached and an exception is raised, it will be propagated up to
            # our caller.
            if self.signals["exception"].count() > 0:
                # If any of the exception handlers return False, then the
                # object is not unregistered from the Notifier.  Otherwise
                # ret = False and it will unregister.
                ret = self.signals["exception"].emit(*sys.exc_info()) == False
            else:
                raise

        # If Notifier callbacks return False, they get unregistered.
        if ret == False:
            self.unregister()
            return False
        return True


class WeakNotifierCallback(WeakCallback, NotifierCallback):

    def _weakref_destroyed(self, object):
        if _python_shutting_down == False:
            super(WeakNotifierCallback, self)._weakref_destroyed(object)
            self.unregister()


class _Wrapper(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, *args, **kwargs):
        init()
        return globals()[self.name](*args, **kwargs)

dispatcher_add = _Wrapper('dispatcher_add')
dispatcher_remove = _Wrapper('dispatcher_remove')
step = _Wrapper('step')
timer_remove = _Wrapper('timer_remove')
timer_add = _Wrapper('timer_add')
socket_remove = _Wrapper('socket_remove')
socket_add = _Wrapper('socket_add')

def shutdown():
    # prefered way to shut down the system
    sys.exit(0)

# socket wrapper

nf_conditions = []
def _socket_add(id, method, condition = 0):
    return nf_socket_add(id, method, nf_conditions[condition])


def _socket_remove(id, condition = 0):
    return nf_socket_remove(id, nf_conditions[condition])


def init( module = None, force_internal=False, **options ):
    global timer_add
    global socket_add
    global dispatcher_add
    global timer_remove
    global socket_remove
    global dispatcher_remove
    global step
    global nf_socket_remove
    global nf_socket_add
    global nf_conditions
    global shutdown

    if not isinstance(timer_add, _Wrapper):
        raise RuntimeError('notifier already initialized')

    if not 'recursive_depth' in options:
        # default value of 2 is not enough when using async yield stuff
        options['recursive_depth'] = 5

    try:
        if force_internal:
            # pynotifier is not allowed
            raise ImportError()
        import notifier
        if notifier.loop:
            raise RuntimeError('pynotifier already initialized')
    except ImportError:
        # use our own copy of pynotifier
        import pynotifier as notifier

    # find a good main notifier implementation
    if not module:
        module = 'generic'
        if sys.modules.has_key('gtk'):
            # The gtk module is loaded, this means that we will hook
            # ourself into the gtk notifier
            module = 'gtk'

    if not module in ('generic', 'gtk', 'twisted_experimental'):
        raise AttributeError('unsupported notifier %s' % module)

    if module == 'twisted_experimental':
        module = 'twisted'

    # use the selected module
    notifier.init(getattr(notifier, module.upper()), **options)

    # delete basic notifier handler
    log = logging.getLogger('notifier')
    for l in log.handlers:
        log.removeHandler(l)

    timer_remove = notifier.timer_remove
    timer_add = notifier.timer_add

    nf_socket_remove = notifier.socket_remove
    nf_socket_add = notifier.socket_add
    nf_conditions = [ notifier.IO_READ, notifier.IO_WRITE ]
    socket_remove = _socket_remove
    socket_add = _socket_add

    dispatcher_add = notifier.dispatcher_add
    dispatcher_remove = notifier.dispatcher_remove

    step = notifier.step

    if module == 'twisted':
        # special stop handling for twisted
        from twisted.internet import reactor
        shutdown = reactor.stop


def _shutdown_weakref_destroyed():
    global _python_shutting_down
    _python_shutting_down = True

atexit.register(_shutdown_weakref_destroyed)
