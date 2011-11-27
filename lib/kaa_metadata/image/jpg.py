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
import time
import logging
import cStringIO
from ..exceptions import *
import core
import EXIF
import IPTC

# get logging object
log = logging.getLogger(__name__)

# interesting file format info:
# http://www.dcs.ed.ac.uk/home/mxr/gfx/2d-hi.html
# http://www.funducode.com/freec/Fileformats/format3/format3b.htm

SOF = { 0xC0 : "Baseline",
        0xC1 : "Extended sequential",
        0xC2 : "Progressive",
        0xC3 : "Lossless",
        0xC5 : "Differential sequential",
        0xC6 : "Differential progressive",
        0xC7 : "Differential lossless",
        0xC9 : "Extended sequential, arithmetic coding",
        0xCA : "Progressive, arithmetic coding",
        0xCB : "Lossless, arithmetic coding",
        0xCD : "Differential sequential, arithmetic coding",
        0xCE : "Differential progressive, arithmetic coding",
        0xCF : "Differential lossless, arithmetic coding",
}

EXIFMap = {
    'Image Artist': 'artist',
    'Image Model': 'hardware',
    'Image Software': 'software',
}

class JPG(core.Image):
    """
    JPEG parser supporting EXIf and IPTC tables. The important
    information is mapped to match the kaa.metadata key naming, the
    complete table can be accessed with self.tables.
    """
    table_mapping = { 'EXIF': EXIFMap, 'IPTC': IPTC.mapping }

    def __init__(self,file):
        core.Image.__init__(self)
        self.mime = 'image/jpeg'
        self.type = 'jpeg image'

        if file.read(2) != '\xff\xd8':
            raise ParseError()

        file.seek(-2,2)
        if file.read(2) != '\xff\xd9':
            # Normally an JPEG should end in ffd9. This does not however
            # we assume it's an jpeg for now
            log.info("Wrong encode found for jpeg")

        file.seek(2)
        app = file.read(4)
        self.meta = {}

        while (len(app) == 4):
            (ff,segtype,seglen) = struct.unpack(">BBH", app)
            if ff != 0xff: break
            if segtype == 0xd9:
                break

            elif SOF.has_key(segtype):
                data = file.read(seglen-2)
                (precision,self.height,self.width,\
                 num_comp) = struct.unpack('>BHHB', data[:6])

            elif segtype == 0xe1:
                data = file.read(seglen-2)
                type = data[:data.find('\0')]
                if type == 'Exif':
                    # create a fake file from the data we have to
                    # pass it to the EXIF parser
                    fakefile = cStringIO.StringIO()
                    fakefile.write('\xFF\xD8')
                    fakefile.write(app)
                    fakefile.write(data)
                    fakefile.seek(0)
                    exif = EXIF.process_file(fakefile)
                    fakefile.close()
                    if exif:
                        self.thumbnail = exif.get('JPEGThumbnail', None)
                        if self.thumbnail:
                            self.thumbnail = str(self.thumbnail)
                        self._appendtable('EXIF', exif)

                        if 'Image Orientation' in exif:
                            orientation = str(exif['Image Orientation'])
                            if orientation.find('90 CW') > 0:
                                self.rotation = 90
                            elif orientation.find('90') > 0:
                                self.rotation = 270
                            elif orientation.find('180') > 0:
                                self.rotation = 180
                        t = exif.get('Image DateTimeOriginal')
                        if not t:
                            # sometimes it is called this way
                            t = exif.get('EXIF DateTimeOriginal')
                        if not t:
                            t = exif.get('Image DateTime')
                        if t:
                            try:
                                t = time.strptime(str(t), '%Y:%m:%d %H:%M:%S')
                                self.timestamp = int(time.mktime(t))
                            except ValueError:
                                # Malformed time string.
                                pass
                elif type == 'http://ns.adobe.com/xap/1.0/':
                    # FIXME: parse XMP data (xml)
                    doc = data[data.find('\0')+1:]
                else:
                    pass

            elif segtype == 0xed:
                iptc = IPTC.parseiptc(file.read(seglen-2))
                if iptc:
                    self._appendtable('IPTC', iptc)

            elif segtype == 0xe7:
                # information created by libs like epeg
                data = file.read(seglen-2)
                if data.count('\n') == 1:
                    key, value = data.split('\n')
                    self.meta[key] = value

            elif segtype == 0xfe:
                self.comment = file.read(seglen-2)
                if self.comment.startswith('<?xml'):
                    # This could be a comment based on
                    # http://www.w3.org/TR/photo-rdf/
                    log.error('xml comment parser not integrated')
                    self.comment = ''
            else:
                # Huffman table marker (FFC4)
                # Start of Scan marker (FFDA)
                # Quantization table marker (FFDB)
                # Restart Interval (FFDD) ???
                if not segtype in [0xc4, 0xda, 0xdb, 0xdd]:
                    log.info("SEGMENT: 0x%x%x, len=%d" % (ff,segtype,seglen))
                file.seek(seglen-2,1)
            app = file.read(4)

        if len(self.meta.keys()):
            self._appendtable('JPGMETA', self.meta)

        for key, value in self.meta.items():
            if key.startswith('Thumb:') or key == 'Software':
                self._set(key, value)


Parser = JPG
