# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# webradio.py - read webradio attributes
# -----------------------------------------------------------------------------
# $Id: webradio.py 2581 2007-03-22 14:16:50Z tack $
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Thomas Schueppel <stain@acm.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------------

__all__ = ['Parser']

# python imports
import urlparse
import string
import urllib

# import kaa.metadata.audio core
import core


# http://205.188.209.193:80/stream/1006

ICY = { 'icy-name': 'title',
        'icy-genre': 'genre',
        'icy-br': 'bitrate',
        'icy-url': 'caption'
      }

class WebRadio(core.Music):

    table_mapping = { 'ICY' : ICY }

    def __init__(self, url):
        core.Music.__init__(self)
        tup = urlparse.urlsplit(url)
        scheme, location, path, query, fragment = tup
        if scheme != 'http':
            raise core.ParseError()

        # Open an URL Connection
        fi = urllib.urlopen(url)

        # grab the statusline
        self.statusline = fi.readline()
        try:
            statuslist = string.split(self.statusline)
        except ValueError:
            # assume it is okay since so many servers are badly configured
            statuslist = ["ICY", "200"]

        if statuslist[1] != "200":
            if fi:
                fi.close()
            raise core.ParseError()

        self.type = 'audio'
        self.subtype = 'mp3'
        # grab any headers for a max of 10 lines
        linecnt = 0
        tab = {}
        lines = fi.readlines(512)
        for linecnt in range(0,11):
            icyline = lines[linecnt]
            icyline = icyline.rstrip('\r\n')
            if len(icyline) < 4:
                break
            cidx = icyline.find(':')
            if cidx != -1:
                # break on short line (ie. really should be a blank line)
                # strip leading and trailing whitespace
                tab[icyline[:cidx].strip()] = icyline[cidx+2:].strip()
        if fi:
            fi.close()
        self._appendtable('ICY', tab)


    def _finalize(self):
        core.Music._finalize(self)
        self.bitrate = string.atoi(self.bitrate)*1000


Parser = WebRadio
