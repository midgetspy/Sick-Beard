# -*- coding: utf-8 -*-
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

__all__ = ['Parser']

import re
import os
import stat
import struct
import logging
from ..exceptions import *
import core

# get logging object
log = logging.getLogger(__name__)

VORBIS_PACKET_INFO = '\01vorbis'
VORBIS_PACKET_HEADER = '\03vorbis'
VORBIS_PACKET_SETUP = '\05vorbis'

class Ogg(core.Music):
    def __init__(self,file):
        core.Music.__init__(self)
        h = file.read(4+1+1+20+1)
        if h[:5] != "OggS\00":
            log.info("Invalid header")
            raise ParseError()
        if ord(h[5]) != 2:
            log.info("Invalid header type flag (trying to go ahead anyway)")
        self.pageSegCount = ord(h[-1])
        # Skip the PageSegCount
        file.seek(self.pageSegCount,1)
        h = file.read(7)
        if h != VORBIS_PACKET_INFO:
            log.info("Wrong vorbis header type, giving up.")
            raise ParseError()

        # http://wiki.xiph.org/index.php/MIME_Types_and_File_Extensions
        self.mime = 'audio/x-vorbis+ogg'
        header = {}
        info = file.read(23)
        self.version, self.channels, self.samplerate, bitrate_max, \
                      self.bitrate, bitrate_min, blocksize, \
                      framing = struct.unpack('<IBIiiiBB',info[:23])
        self.bitrate = self.bitrate / 1000
        # INFO Header, read Oggs and skip 10 bytes
        h = file.read(4+10+13)
        if h[:4] == 'OggS':
            (serial, pagesequence, checksum, numEntries) = \
                     struct.unpack('<14xIIIB', h)
            # skip past numEntries
            file.seek(numEntries,1)
            h = file.read(7)
            if h != VORBIS_PACKET_HEADER:
                # Not a corrent info header
                return
            self.encoder = self._extractHeaderString(file)
            numItems = struct.unpack('<I',file.read(4))[0]
            for i in range(numItems):
                s = self._extractHeaderString(file)
                a = re.split('=',s)
                header[(a[0]).upper()]=a[1]
            # Put Header fields into info fields
            if header.has_key('TITLE'):
                self.title = header['TITLE']
            if header.has_key('ALBUM'):
                self.album = header['ALBUM']
            if header.has_key('ARTIST'):
                self.artist = header['ARTIST']
            if header.has_key('COMMENT'):
                self.comment = header['COMMENT']
            if header.has_key('DATE'):
                # FIXME: try to convert to timestamp
                self.userdate = header['DATE']
            if header.has_key('ENCODER'):
                self.encoder = header['ENCODER']
            if header.has_key('TRACKNUMBER'):
                self.trackno = header['TRACKNUMBER']
            self.type = 'OGG Vorbis'
            self.subtype = ''
            self.length = self._calculateTrackLength(file)
            self._appendtable('VORBISCOMMENT',header)


    def _extractHeaderString(self,f):
        len = struct.unpack( '<I', f.read(4) )[0]
        return unicode(f.read(len), 'utf-8')


    def _calculateTrackLength(self,f):
        # seek to the end of the stream, to avoid scanning the whole file
        if (os.stat(f.name)[stat.ST_SIZE] > 20000):
            f.seek(os.stat(f.name)[stat.ST_SIZE]-10000)

        # read the rest of the file into a buffer
        h = f.read()
        granule_position = 0
        # search for each 'OggS' in h
        if len(h):
            idx = h.rfind('OggS')
            if idx < 0:
                return 0
            pageSize = 0
            h = h[idx+4:]
            (check, type, granule_position, absPos, serial, pageN, crc, \
             segs) = struct.unpack('<BBIIIIIB', h[:23])
            if check != 0:
                log.debug(h[:10])
                return
            log.debug("granule = %d / %d" % (granule_position, absPos))
        # the last one is the one we are interested in
        return float(granule_position) / self.samplerate


Parser = Ogg
