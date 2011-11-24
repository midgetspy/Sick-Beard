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

import struct
import re
import logging
import core
from ..exceptions import *

# get logging object
log = logging.getLogger(__name__)

# See: http://flac.sourceforge.net/format.html

class Flac(core.Music):
    def __init__(self,file):
        core.Music.__init__(self)
        if file.read(4) != 'fLaC':
            raise ParseError()

        # http://wiki.xiph.org/index.php/MIME_Types_and_File_Extensions
        self.mime = 'audio/flac'
        self.codec = 0xF1AC # fourcc code of flac

        while 1:
            (blockheader,) = struct.unpack('>I',file.read(4))
            lastblock = (blockheader >> 31) & 1
            type = (blockheader >> 24) & 0x7F
            numbytes = blockheader & 0xFFFFFF
            log.debug("Last?: %d, NumBytes: %d, Type: %d" % \
                      (lastblock, numbytes, type))
            # Read this blocks the data
            data = file.read(numbytes)
            if type == 0:
                # STREAMINFO
                bits = struct.unpack('>L', data[10:14])[0]
                self.samplerate = (bits >> 12) & 0xFFFFF
                self.channels = ((bits >> 9) & 7) + 1
                self.samplebits = ((bits >> 4) & 0x1F) + 1
                md5 = data[18:34]
                # Number of samples is bits 108-144 in block.
                samples = ((ord(data[13]) & 0x0f) << 32) + struct.unpack('>L', data[14:18])[0]
                self.length = float(samples) / self.samplerate
            elif type == 1:
                # PADDING
                pass
            elif type == 2:
                # APPLICATION
                pass
            elif type == 3:
                # SEEKTABLE
                pass
            elif type == 4:
                # VORBIS_COMMENT
                skip, self.vendor = self._extractHeaderString(data)
                num, = struct.unpack('<I', data[skip:skip+4])
                start = skip+4
                header = {}
                for i in range(num):
                    (nextlen, s) = self._extractHeaderString(data[start:])
                    start += nextlen
                    a = re.split('=',s)
                    header[(a[0]).upper()]=a[1]

                map = {
                    u'TITLE': 'title', u'ALBUM': 'album', u'ARTIST': 'artist', u'COMMENT': 'comment',
                    u'ENCODER': 'encoder', u'TRACKNUMBER': 'trackno', u'TRACKTOTAL': 'trackof',
                    # FIXME: try to convert userdate to timestamp
                    u'DATE': 'userdate',
                }
                for key, attr in map.items():
                    if key in header:
                        setattr(self, attr, header[key])

                self._appendtable('VORBISCOMMENT', header)
            elif type == 5:
                # CUESHEET
                pass
            else:
                # UNKNOWN TYPE
                pass
            if lastblock:
                break

    def _extractHeaderString(self,header):
        len = struct.unpack('<I', header[:4])[0]
        return (len+4,unicode(header[4:4+len], 'utf-8'))


Parser = Flac
