# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# event.py - Event handling for the main loop
# -----------------------------------------------------------------------------
# $Id: event.py 4070 2009-05-25 15:32:31Z tack $
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

__all__ = [ 'Event', 'EventHandler', 'WeakEventHandler' ]

# python imports
import copy
import logging

# kaa.base imports
from nf_wrapper import NotifierCallback, WeakNotifierCallback
from thread import MainThreadCallback, is_mainthread
from timer import OneShotTimer
from utils import property

# get logging object
log = logging.getLogger('base')

# manager object for eveny handling
manager = None

class Event(object):
    """
    A simple event that can be passed to the registered event handler.
    """
    def __init__(self, name, *args):
        """
        Init the event.
        """
        if isinstance(name, Event):
            self.name = name.name
            self.arg  = name.arg
        else:
            self.name = name
            self.arg  = None
        if args:
            self._set_args(args)


    def _set_args(self, args):
        """
        Set arguments of the event.
        """
        if not args:
            self.arg = None
        elif len(args) == 1:
            self.arg = args[0]
        else:
            self.arg = args


    def post(self, *args):
        """
        Post event into the queue.
        """
        event = self
        if args:
            event = copy.copy(self)
            event._set_args(args)
        if not is_mainthread():
            return MainThreadCallback(manager.post, event)()
        else:
            return manager.post(event)


    def __str__(self):
        """
        Return the event as string
        """
        return self.name


    def __cmp__(self, other):
        """
        Compare function, return 0 if the objects are identical, 1 otherwise
        """
        if not other:
            return 1
        if isinstance(other, Event):
            return self.name != other.name
        return self.name != other


class EventHandler(NotifierCallback):
    """
    Event handling callback.
    """
    def register(self, events=[]):
        """
        Register to a list of events. If no event is given, all events
        will be used.
        """
        self.events = events
        if not self in manager.handler:
            manager.handler.append(self)


    @property
    def active(self):
        """
        True if the object is bound to the event manager.
        """
        return self in manager.handler


    def unregister(self):
        """
        Unregister callback.
        """
        if self in manager.handler:
            manager.handler.remove(self)


    def __call__(self, event):
        """
        Call callback if the event matches.
        """
        if not self.events or event in self.events:
            super(EventHandler, self).__call__(event)


class WeakEventHandler(WeakNotifierCallback, EventHandler):
    """
    Weak reference version of the EventHandler.
    """
    pass


class EventManager(object):
    """
    Class to manage Event and EventHandler objects.
    Internal use only.
    """
    def __init__(self):
        self.queue = []
        self.locked = False
        self.timer = OneShotTimer(self.handle)
        self.handler = []


    def post(self, event):
        """
        Add event to the queue.
        """
        self.queue.append(event)
        if not self.timer.active:
            self.timer.start(0)


    def handle(self):
        """
        Handle the next event.
        """
        if self.locked:
            self.timer.start(0.01)
            return
        if not self.queue:
            return
        self.locked = True
        event = self.queue[0]
        self.queue = self.queue[1:]

        try:
            for handler in copy.copy(self.handler):
                handler(event)
        except Exception, e:
            log.exception('event callback')
        self.locked = False
        if self.queue and not self.timer.active:
            self.timer.start(0)

manager = EventManager()
