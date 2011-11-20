# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# dateutils.py - Date/time utility functions and objects.
# -----------------------------------------------------------------------------
# $Id: dateutils.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# Copyright 2009 Dirk Meyer, Jason Tackaberry
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

from datetime import datetime, tzinfo, timedelta
import time

__all__ = ['utc', 'local', 'utc2localtime', 'localtime2utc']

# XXX: I'm not fond of these two functions.  Unix timestamps are by convention
# in UTC.  Dealing with timestamps as seconds since epoch in localtime is
# unconventional and confusing IMHO.  Consider removing these.
def utc2localtime(t):
    """
    Transform given seconds from UTC into localtime
    """
    if not t:
        # no time value given
        return 0
    # FIXME: maybe cache this value
    # time.daylight does not do what we want
    if time.localtime(time.time())[8]:
        return t - time.altzone
    else:
        return t - time.timezone


def localtime2utc(t):
    """
    Transform given seconds from localtime into UTC
    """
    if not t:
        # no time value given
        return 0
    # FIXME: maybe cache this value
    # time.daylight does not do what we want
    if time.localtime(time.time())[8]:
        return t + time.altzone
    else:
        return t + time.timezone


# UTC and Local tzinfo classes, more or less from the python docs.

class TZUTC(tzinfo):
    'UTC timezone'
    ZERO = timedelta(0)
    tzname = lambda self, dt: 'UTC'
    utcoffset = lambda self, dt: TZUTC.ZERO
    dst = lambda self, dt: TZUTC.ZERO
 

class TZLocal(tzinfo):
    'DST-aware local time zone'
    STDOFFSET = timedelta(seconds = -time.timezone)
    DSTOFFSET = timedelta(seconds = -time.altzone) if time.daylight else timedelta(seconds = -time.timezone)

    tzname = lambda self, dt: time.tzname[self._isdst(dt)]
    utcoffset = lambda self, dt: TZLocal.DSTOFFSET if self._isdst(dt) else TZLocal.STDOFFSET
    dst = lambda self, dt: (TZLocal.DSTOFFSET - TZLocal.STDOFFSET) if self._isdst(dt) else TZUTC.ZERO

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        return time.localtime(time.mktime(tt)).tm_isdst > 0

# These can be used whenever tzinfo objects are required in datetime functions/methods.
utc = TZUTC()   
local = TZLocal()

