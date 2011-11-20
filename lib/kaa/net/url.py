# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# url.py - wrapper for receiving urllib2.Request objects
# -----------------------------------------------------------------------------
# $Id: url.py 4088 2009-05-25 20:58:44Z dmeyer $
#
# Usage:
# request = urllib2.Request('http://www.freevo.org/')
# url = URLOpener(request)
# url.signals['header'].connect(callback)
# url.signals['data'].connect(callback)
# url.signals['completed'].connect(callback)
# url.fetch(length=0) -> InProgress object
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

__all__ = [ 'URLOpener', 'fetch', 'add_password' ]

# python imports
import os
import stat
import urllib
import urllib2

# kaa imports
from kaa import ThreadCallback, InProgressStatus, Signals, InProgress

# add password manager to urllib
pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
urllib2.install_opener(urllib2.build_opener(urllib2.HTTPBasicAuthHandler(pm)))

# expose add_password function from HTTPPasswordMgrWithDefaultRealm
add_password = pm.add_password

class URLOpener(object):
    """
    Thread based urlopen2.urlopen function.
    Note: if special opener (see urlib2) are used, they are executed inside
    the thread. Make sure the code is thread safe.
    """
    def __init__(self, request, data = None):
        self._args = request, data
        self.signals = Signals('header', 'data')


    def fetch(self, length=0):
        """
        Start urllib2 data fetching. If length is 0 the complete data will
        be fetched and send to the data and completed signal. If data is
        greater 0, the fd will read 'length' bytes and send it to the data
        signal until everything is read or no callback is connected anymore.
        The function returns the 'completed' signal which is an InProgress
        object.
        """
        t = ThreadCallback(self._fetch_thread, length)
        t.wait_on_exit = False
        return t()


    def _fetch_thread(self, length):
        """
        The real urllib2 calls in a thread.
        """
        try:
            fd = urllib2.urlopen(*self._args)
        except urllib2.HTTPError, e:
            # FIXME: how to handle this.
            return e.code
        self.signals['header'].emit(fd.info())
        if length and not len(self.signals['data']):
            # no callback connected, no need to read
            return
        if not length:
            # get everything at once
            data = fd.read()
            self.signals['data'].emit(data)
            return data
        while True:
            # read in length data size chunks
            data = fd.read(length)
            self.signals['data'].emit(data)
            if not data:
                # no data (done)
                return True
            if not len(self.signals['data']):
                # no callback listening anymore
                return False


def _fetch_HTTP(url, filename, tmpname):
    """
    Fetch HTTP URL.
    """
    def download(url, filename, tmpname, status):
        src = urllib2.urlopen(url)
        length = int(src.info().get('Content-Length', 0))
        if not tmpname:
            tmpname = filename
        dst = open(tmpname, 'w')
        status.set(0, length)
        while True:
            data = src.read(1024)
            if len(data) == 0:
                src.close()
                dst.close()
                if length and os.stat(tmpname)[stat.ST_SIZE] != length:
                    # something went wrong
                    os.unlink(tmpname)
                    raise IOError('download %s failed' % url)
                if tmpname != filename:
                    os.rename(tmpname, filename)
                return True
            status.update(len(data))
            dst.write(data)

    if url.find(' ') > 0:
        # stupid url encoding in url
        url = url[:8+url[8:].find('/')] + \
              urllib.quote(url[8+url[8:].find('/'):])
    # FIXME: use kaa.threaded()
    s = InProgressStatus()
    t = ThreadCallback(download, url, filename, tmpname, s)
    t.wait_on_exit = False
    async = t()
    async.progress = s
    return async


def fetch(url, filename, tmpname=None):
    """
    Generic fetch function. If tmpname is given download to this filename
    first and move the file if the download is finished.
    """
    if url.startswith('http://') or url.startswith('https://'):
        return _fetch_HTTP(url, filename, tmpname)
    raise RuntimeError('unable to fetch %s' % url)
