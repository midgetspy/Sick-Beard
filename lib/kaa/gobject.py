# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# glib.py - Glib (gobject mainloop) thread wrapper
# -----------------------------------------------------------------------------
# $Id: gobject.py 4070 2009-05-25 15:32:31Z tack $
#
# This module makes it possible to run the glib mainloop in an extra thread
# and provides a hook to run callbacks in the glib thread. This module also
# supports using the glib mainloop as main mainloop. In that case, no threads
# are used.
#
# If you use this module to interact with a threaded glib mainloop, remember
# that callbacks from glib are also called from the glib thread.
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2008-2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'GOBJECT', 'gobject_set_threaded' ]

# python imports
import threading

# get import helper since this file conflicts with the
# global gobject module.
from utils import sysimport
try:
    # try to import gobject
    gobject = sysimport('gobject')
except ImportError:
    gobject = None

# get thread module
import thread as thread_support
import main as main_module

# object for kaa.threaded decorator
GOBJECT = object()

class Wrapper(object):
    """
    Glib wrapper with JobServer interface.
    """
    def __init__(self):
        # register this class as thread.JobServer
        thread_support._threads[GOBJECT] = self
        self.stopped = False
        self.thread = False
        self.init = False

    def set_threaded(self, mainloop=None):
        """
        Start the gobject mainloop in a thread. This function should
        always be used together with the generic mainloop.  It is
        possible to jump between the gobject and the generic mainloop
        with the threaded decorator.

        :param mainloop: the mainloop object to use a mainloop based on gobject
          like the gstreamer or clutter mainloop. The object provided here must
          have a start and a stop function.
        """
        if self.init:
            raise RuntimeError('gobject loop already running')
        if self.thread:
            return
        self.thread = True
        if gobject is not None:
            # init thread support in the module importing gobject
            gobject.threads_init()
            self.loop(mainloop)
            # make sure we get a clean shutdown
            main_module.signals['shutdown'].connect_once(self.stop, True)

    @thread_support.threaded()
    def loop(self, mainloop):
        """
        Glib thread.
        """
        self.thread = threading.currentThread()
        if mainloop is None:
            mainloop = gobject.MainLoop()
        self._loop = mainloop
        self._loop.run()

    def add(self, callback):
        """
        Add a callback.
        """
        self.init = True
        if not self.thread or threading.currentThread() == self.thread:
            return callback()
        gobject.idle_add(self._execute, callback)

    def _execute(self, callback):
        """
        Execute callback.
        """
        if callback is not None:
            callback()
        elif self.stopped:
            self._loop.quit()
        return False

    def stop(self, wait=False):
        """
        Stop the glib thread.
        """
        if not self.stopped:
            self.stopped = True
            if self.thread:
                self.add(None)
        if wait:
            # wait until the thread is done
            self.join()

    def join(self):
        """
        Wait until the thread is done.
        """
        if self.thread:
            # join the thread
            self.thread.join()

# create object and expose set_threaded
gobject_set_threaded = Wrapper().set_threaded
