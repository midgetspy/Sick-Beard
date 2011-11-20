# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# lirc.py - Lirc input module
# -----------------------------------------------------------------------------
# $Id: lirc.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# kaa.input - Kaa input subsystem
# Copyright 2005-2009 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'init', 'stop' ]

# python imports
import os
import time

# kaa imports
import kaa

try:
    # try to import python lirc module
    import pylirc
except ImportError:
    # pylirc not installed
    pylirc = None


_key_delay_map = [ 0.4, 0.2, 0.2, 0.15, 0.1 ]
_last_code = None
_key_delay_times = None
_last_key_time = 0
_dispatcher = None

# make sure we have the lirc signal, no matter
# if lirc is working or not
signal = kaa.Signal()
kaa.signals["lirc"] = signal

def _handle_lirc_input():
    """
    callback to handle a button press.
    """

    global _key_delay_times, _last_code, _repeat_count, _last_key_time

    now = time.time()
    codes = pylirc.nextcode()

    if codes == None:
        # Either end of repeat, or just a delay between repeats...
        if _last_key_time + _key_delay_map[0] + 0.05 <= now:
            # Too long since the last key, so reset
            _last_key_time = 0
            _repeat_count = 0
        return

    elif codes == []:
        if not _key_delay_times:
            return True
        # Repeat last key iff we've passed the required key delay
        i = min(_repeat_count, len(_key_delay_times) - 2)
        delay = now - _key_delay_times[i][1]
        if delay >= _key_delay_times[i + 1][0]:
            codes = [ _last_code ]
            _key_delay_times[i + 1][1] = now
            _repeat_count += 1
        else:
            return True

    else:
        _key_delay_times = [[0, now]] + [ [x, 0] for x in _key_delay_map ]
        _repeat_count = 0

    _last_key_time = now
    for code in codes:
        signal.emit(code)
        _last_code = code

    return True


def stop():
    """
    Callback for shutdown.
    """
    global _dispatcher
    if not _dispatcher:
        # already disconnected
        return
    _dispatcher.unregister()
    _dispatcher = None
    pylirc.exit()
    kaa.main.signals["shutdown"].disconnect(stop)


def init(appname = None, cfg = None):
    """
    Init pylirc and connect to the mainloop.
    """
    global _dispatcher

    if _dispatcher:
        # already running
        return False

    if not pylirc:
        # not installed
        return False

    if cfg == None:
        cfg = os.path.expanduser("~/.lircrc")
    if appname == None:
        appname = "kaa"

    try:
        fd = pylirc.init(appname, cfg)
    except IOError:
        # something went wrong
        return False

    if not fd:
        # something went wrong
        return False

    pylirc.blocking(0)
    _dispatcher = kaa.IOMonitor(_handle_lirc_input)
    _dispatcher.register(fd)
    kaa.main.signals["shutdown"].connect(stop)

    return True


if __name__ == "__main__":
    """
    Some test code
    """
    init()
    def cb(code):
        print "CODE", code
    signal.connect(cb)
    kaa.main.run()
