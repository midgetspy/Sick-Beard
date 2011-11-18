# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# nf_thread.py - Thread based notifier to include in other mainloops
# -----------------------------------------------------------------------------
# $Id: nf_thread.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2007-2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'init' ]

# python imports
import threading
import logging

# kaa imports
import main
import nf_wrapper as notifier
from main import _set_running as set_mainloop_running

# get logging object
log = logging.getLogger('notifier')

class ThreadLoop(threading.Thread):
    """
    Thread running the kaa mainloop.
    """
    def __init__(self, interleave, shutdown = None):
        super(ThreadLoop, self).__init__()
        if shutdown is not None:
            # special shutdown function
            notifier.shutdown = shutdown
        self._call_mainloop = interleave
        self._lock = threading.Semaphore(0)
        self.sleeping = False


    def handle(self):
        """
        Callback from the real mainloop.
        """
        try:
            try:
                notifier.step(sleep = False)
            except (KeyboardInterrupt, SystemExit):
                set_mainloop_running(False)
                notifier.shutdown()
        finally:
            self._lock.release()


    def run(self):
        """
        Thread part running the blocking, simulating loop.
        """
        set_mainloop_running(True)
        try:
            while True:
                self.sleeping = True
                notifier.step(simulate = True)
                self.sleeping = False
                if not main.is_running():
                    break
                self._call_mainloop(self.handle)
                self._lock.acquire()
                if not main.is_running():
                    break
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception, e:
            log.exception('loop')
        if main.is_running():
            # this loop stopped, call real mainloop stop. This
            # should never happen because we call no callbacks.
            log.warning('thread loop stopped')
            set_mainloop_running(False)
            self._call_mainloop(self.notifier.shutdown)


    def stop(self):
        """
        Stop the thread and cleanup.
        """
        log.info('stop mainloop')
        set_mainloop_running(False)
        main.wakeup()
        main.stop()


class TwistedLoop(ThreadLoop):
    """
    Thread based mainloop in Twisted.
    """
    def __init__(self):
        from twisted.internet import reactor
        reactor.addSystemEventTrigger('after', 'shutdown', self.stop)
        super(TwistedLoop, self).__init__(reactor.callFromThread, reactor.stop)


class Wakeup(object):
    """
    Wrapper around a function to wakeup the sleeping mainloop
    when timer or sockets are added.
    """
    def __init__(self, loop, func):
        self.loop = loop
        self.func = func

    def __call__(self, *args, **kwargs):
        ret = self.func(*args, **kwargs)
        if self.loop.sleeping:
            main.wakeup()
        return ret


def init( module, handler = None, shutdown = None, **options ):
    """
    Init the notifier.
    """
    if module == 'twisted':
        loop = TwistedLoop()
    elif module == 'thread':
        if not handler:
            raise RuntimeError('no callback handler provided')
        loop = ThreadLoop(handler, shutdown)
    else:
        raise RuntimeError('unknown notifier module %s', module)
    notifier.init( 'generic', force_internal=True, **options )
    if shutdown is not None:
        # set specific shutdown function
        notifier.shutdown = shutdown
    # set main thread and init thread pipe
    main.set_as_mainthread()
    # adding a timer or socket is not thread safe in general but
    # an additional wakeup we don't need does not hurt. And in
    # simulation mode the step function does not modify the
    # internal variables.
    notifier.timer_add = Wakeup(loop, notifier.timer_add)
    notifier.socket_add = Wakeup(loop, notifier.socket_add)
    loop.start()
    return loop
