#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: Andreas Büsching <crunchy@bitkipper.net>
#
# package initialisation
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA

"""Simple mainloop that watches sockets and timers."""

from version import *

from select import select

import log

socket_add = None
socket_remove = None

timer_add = None
timer_remove = None

dispatcher_add = None
dispatcher_remove = None

loop = None
step = None

# notifier types
( GENERIC, QT, GTK, WX, TWISTED ) = range( 5 )

# socket conditions
IO_READ = None
IO_WRITE = None
IO_EXCEPT = None

def init( model = GENERIC, **kwargs ):
	global timer_add
	global socket_add
	global dispatcher_add
	global timer_remove
	global socket_remove
	global dispatcher_remove
	global loop, step
	global IO_READ, IO_WRITE, IO_EXCEPT

	if model == GENERIC:
		import nf_generic as nf_impl
	elif model == QT:
		import nf_qt as nf_impl
	elif model == GTK:
		import nf_gtk as nf_impl
	elif model == WX:
		import nf_wx as nf_impl
		log.warn( 'the WX notifier is deprecated and is no longer maintained' )
	elif model == TWISTED:
		import nf_twisted as nf_impl
		log.info("using nf_twisted")
	else:
		raise Exception( 'unknown notifier model' )

	socket_add = nf_impl.socket_add
	socket_remove = nf_impl.socket_remove
	timer_add = nf_impl.timer_add
	timer_remove = nf_impl.timer_remove
	dispatcher_add = nf_impl.dispatcher_add
	dispatcher_remove = nf_impl.dispatcher_remove
	loop = nf_impl.loop
	step = nf_impl.step
	IO_READ = nf_impl.IO_READ
	IO_WRITE = nf_impl.IO_WRITE
	IO_EXCEPT = nf_impl.IO_EXCEPT

	if hasattr( nf_impl, '_options' ) and type( nf_impl._options ) == dict:
		for k, v in kwargs.items():
			if nf_impl._options.has_key( k ):
				nf_impl._options[ k ] = v

	if hasattr( nf_impl, '_init' ):
		nf_impl._init()

class Callback:
	def __init__( self, function, *args ):
		self._function = function
		self._args = args

	def __call__( self, *args ):
		tmp = list( args )
		if self._args:
			tmp.extend( self._args )
		if tmp:
			return self._function( *tmp )
		else:
			return self._function()

	def __cmp__( self, rvalue ):
		if not callable( rvalue ): return -1

		if ( isinstance( rvalue, Callback ) and \
			   self._function == rvalue._function ) or \
			   self._function == rvalue:
			return 0

		return -1

	def __nonzero__( self ):
		return bool( self._function )

	def __hash__( self ):
		return self._function.__hash__()
