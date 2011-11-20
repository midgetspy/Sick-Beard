# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# logger.py - Updates to the Python logging module
# -----------------------------------------------------------------------------
# $Id: logger.py 4070 2009-05-25 15:32:31Z tack $
#
# This module 'fixes' the Python logging module to accept fixed string and
# unicode arguments. It will also make sure that there is a logging handler
# defined when needed.
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

# Python imports
import logging

# baa.base imports
from strutils import unicode_to_str


def create_logger(level = logging.WARNING):
    """
    Create a simple logging object for applicatins that don't want
    to create a logging handler on their own. You should always have
    a logging object.
    """
    '''
    log = logging.getLogger()
    # delete current handler
    for l in log.handlers:
        log.removeHandler(l)

    # Create a simple logger object
    if len(logging.getLogger().handlers) > 0:
        # there is already a logger, skipping
        return

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s(%(lineno)s): %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    '''


_makeRecord = logging.Logger.makeRecord

def make_record(self, name, level, fn, lno, msg, args, *_args, **_kwargs):
    """
    A special makeRecord class for the logger to convert msg and args into
    strings using the correct encoding if they are unicode strings. This
    function also makes sure we have at least a basic handler.
    """
    '''
    if len(self.root.handlers) == 0:
        # create handler, we don't have one
        create_logger()

    # convert message to string
    msg = unicode_to_str(msg)
    # convert args to string
    args = tuple([ unicode_to_str(x) for x in args ])
    # call original function
    return _makeRecord(self, name, level, fn, lno, msg, args, *_args, **_kwargs)
    '''

# override makeRecord of a logger by our new function that can handle
# unicode correctly and that will take care of a basic logger.
# logging.Logger.makeRecord = make_record
