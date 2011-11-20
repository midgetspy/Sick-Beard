#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Andreas Büsching <crunchy@bitkipper.net>
#
# notifier wrapper for GTK+ 2.x
#
# Copyright 2004, 2005, 2006
#		Andreas Büsching <crunchy@bitkipper.net>
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

"""Simple mainloop that watches sockets and timers."""

import gobject

import dispatch
import log

IO_READ = gobject.IO_IN
IO_WRITE = gobject.IO_OUT
IO_EXCEPT = gobject.IO_ERR

_options = {
	'x11' : True,
}

# map of Sockets/Methods -> GTK source IDs
_gtk_socketIDs = {}
_gtk_socketIDs[ IO_READ ] = {}
_gtk_socketIDs[ IO_WRITE ] = {}

def socket_add( socket, method, condition = IO_READ ):
	"""The first argument specifies a socket, the second argument has to be a
	function that is called whenever there is data ready in the socket."""
	global _gtk_socketIDs
	source = gobject.io_add_watch( socket, condition,
								   _socket_callback, method )
	_gtk_socketIDs[ condition ][ socket ] = source

def _socket_callback( source, condition, method ):
	"""This is an internal callback function, that maps the GTK source IDs
	to the socket objects that are used by pynotifier as an identifier
	"""
	global _gtk_socketIDs
	if _gtk_socketIDs[ condition ].has_key( source ):
		ret = method( source )
		if not ret:
			socket_remove( source, condition )
	return ret

	log.info( "socket '%s' not found" % source )
	return False

def socket_remove( socket, condition = IO_READ ):
	"""Removes the given socket from scheduler."""
	global _gtk_socketIDs
	if _gtk_socketIDs[ condition ].has_key( socket ):
		gobject.source_remove( _gtk_socketIDs[ condition ][ socket ] )
		del _gtk_socketIDs[ condition ][ socket ]
	else:
		log.info( "socket '%s' not found" % socket )

def timer_add( interval, method ):
	"""The first argument specifies an interval in milliseconds, the
	second argument a function. This is function is called after
	interval seconds. If it returns true it's called again after
	interval seconds, otherwise it is removed from the scheduler. The
	third (optional) argument is a parameter given to the called
	function."""
	return gobject.timeout_add( interval, method )

def timer_remove( id ):
	"""Removes the timer specified by id from the scheduler."""
	gobject.source_remove( id )

dispatcher_add = dispatch.dispatcher_add
dispatcher_remove = dispatch.dispatcher_remove

_mainloop = None
_step = None

def step( sleep = True, external = True ):
	global _step
	_step( sleep )
	if external:
		dispatch.dispatcher_run()

def loop():
	"""Execute main loop forever."""
	while 1:
		step()

def _init():
	global _step, _mainloop

	if _options[ 'x11' ] == True:
		import gtk
		_step = gtk.main_iteration_do
	else:
		_mainloop = gobject.main_context_default()
		_step = _mainloop.iteration

	gobject.threads_init()
