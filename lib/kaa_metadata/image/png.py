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
import zlib
import logging
from ..exceptions import *
import core
from ..strutils import str_to_unicode

# get logging object
log = logging.getLogger(__name__)

# interesting file format info:
# http://www.libpng.org/pub/png/png-sitemap.html#programming
# http://pmt.sourceforge.net/pngmeta/
# http://www.libpng.org/pub/png/spec/1.2/PNG-Chunks.html

PNGSIGNATURE = "\211PNG\r\n\032\n"


class PNG(core.Image):

    def __init__(self,file):
        core.Image.__init__(self)
        self.mime = 'image/png'
        self.type = 'PNG image'

        signature = file.read(8)
        if signature != PNGSIGNATURE:
            raise ParseError()

        self.meta = {}
        while self._readChunk(file):
            pass
        if len(self.meta.keys()):
            self._appendtable('PNGMETA', self.meta)
        for key, value in self.meta.items():
            if key.startswith('Thumb:') or key == 'Software':
                self._set(key, value)


    def _readChunk(self,file):
        try:
            (length, type) = struct.unpack('>I4s', file.read(8))
        except (OSError, IOError, struct.error):
            return 0

        key = None

        if type == 'IEND':
            return 0

        elif type == 'IHDR':
            data = file.read(length+4)
            self.width, self.height, self.depth = struct.unpack(">IIb", data[:9])

        elif type == 'tEXt':
            log.debug('latin-1 Text found.')
            (data, crc) = struct.unpack('>%isI' % length,file.read(length+4))
            (key, value) = data.split('\0')
            self.meta[key] = str_to_unicode(value)

        elif type == 'zTXt':
            log.debug('Compressed Text found.')
            (data,crc) = struct.unpack('>%isI' % length,file.read(length+4))
            split = data.split('\0')
            key = split[0]
            value = "".join(split[1:])
            compression = ord(value[0])
            value = value[1:]
            if compression == 0:
                decompressed = zlib.decompress(value)
                log.debug("%s (Compressed %i) -> %s" % \
                          (key,compression,decompressed))
            else:
                log.debug("%s has unknown Compression %c" % (key,compression))
            self.meta[key] = str_to_unicode(value)

        elif type == 'iTXt':
            log.debug('International Text found.')
            (data,crc) = struct.unpack('>%isI' % length,file.read(length+4))
            (key, value) = data.split('\0')
            self.meta[key] = str_to_unicode(value)

        else:
            file.seek(length+4,1)
            log.debug("%s of length %d ignored." % (type, length))

        if key is not None and key.lower() == "comment":
            self.comment = self.meta[key]
        return 1


Parser = PNG
