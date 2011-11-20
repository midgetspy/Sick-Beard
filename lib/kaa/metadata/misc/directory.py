# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# directory.py - parse directory information
# -----------------------------------------------------------------------------
# $Id: directory.py 3647 2008-10-25 19:52:16Z hmeine $
#
# -----------------------------------------------------------------------------
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
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
# -----------------------------------------------------------------------------

__all__ = ['Parser']

# python imports
import os
import logging

# kaa imports
import kaa

# kaa.metadata imports
import kaa.metadata.core as core
from kaa.metadata.image.core import BinsParser

# get logging object
log = logging.getLogger('metadata')

class Directory(core.Media):
    """
    Simple parser for reading a .directory file.
    """
    media = core.MEDIA_DIRECTORY

    def __init__(self, directory):
        core.Media.__init__(self)

        # search .directory
        info = os.path.join(directory, '.directory')
        if os.path.isfile(info):
            f = open(info)
            for l in f.readlines():
                if l.startswith('Icon='):
                    image = l[5:].strip()
                    if not image.startswith('/'):
                        image = os.path.join(directory, image)
                    if os.path.isfile(image):
                        self._set('image', image)
                if l.startswith('Name='):
                    self.title = l[5:].strip()
                if l.startswith('Comment='):
                    self.comment = l[8:].strip()
            f.close()

        # search album.xml (bins)
        binsxml = os.path.join(directory, 'album.xml')
        if os.path.isfile(binsxml):
            bins = BinsParser(binsxml)
            for key, value in bins.items():
                if key == 'sampleimage':
                    image = os.path.join(directory, kaa.unicode_to_str(value))
                    if os.path.isfile(image):
                        self._set('image', image)
                    continue
                self._set(key, value)

        # find folder.jpg (windows style cover)
        folderjpg = os.path.join(directory, 'folder.jpg')
        if os.path.isfile(folderjpg):
            self._set('image', folderjpg)

        self.mime = 'text/directory'

Parser = Directory
