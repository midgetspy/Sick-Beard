# -*- coding: utf-8 -*-
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2009 Dirk Meyer
#
# First Edition: Dirk Meyer <dischi@freevo.org>
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

import time
import core
import exiv2

mapping = {
    # Generic mapping
    'Image.Width': 'width',
    'Image.Height': 'height',
    'Image.Mimetype': 'mime',
    'Image.Thumbnail': 'thumbnail',
    'Image.Keywords': 'keywords',

    # EXIF mapping
    'Exif.Image.Model': 'hardware',
    'Exif.Image.Software': 'software',
    'Exif.Canon.OwnerName': 'artist',

    # IPTC mapping
    'Iptc.Application2.Byline': 'artist',
    'Iptc.Application2.BylineTitle': 'title',
    'Iptc.Application2.Headline': 'title',
    'Iptc.Application2.Writer': 'author',
    'Iptc.Application2.Credit': 'author',
    'Iptc.Application2.Byline': 'author',
    'Iptc.Application2.LocationName': 'country',
    'Iptc.Application2.Caption': 'description',
    'Iptc.Application2.City': 'city',
    'Iptc.Application2.SubLocation': 'location'
}

# use 'mminfo -d 2 filename' to get a list of detected attributes if
# you want to improve this list

class Generic(core.Image):

    table_mapping = { 'exiv2': mapping }

    def __init__(self, file):
        core.Image.__init__(self)
        self.type = 'image'
        # The exiv2 parser just dumps everything it sees in a dict.
        # The mapping from above is used to convert the exiv2 keys to
        # kaa.metadata keys.
        metadata = exiv2.parse(file.name)
        self._appendtable('exiv2', metadata)

        # parse timestamp
        t = metadata.get('Exif.Photo.DateTimeOriginal')
        if not t:
            # try the normal timestamp which may be last-modified
            t = metadata.get('Exif.Image.DateTime')
        if t:
            try:
                t = time.strptime(str(t), '%Y:%m:%d %H:%M:%S')
                self.timestamp = int(time.mktime(t))
            except ValueError:
                # Malformed time string.
                pass

        # parse orientation
        orientation = metadata.get('Exif.Image.Orientation')
        if orientation == 2:
            self.rotation = 180
        if orientation == 5:
            self.rotation = 270
        if orientation == 6:
            self.rotation = 90

Parser = Generic
