# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# gif.py - gif file parsing
# -----------------------------------------------------------------------------
# $Id: gif.py 3982 2009-05-14 18:51:38Z tack $
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
import struct
import logging

# import kaa.metadata.image core
import core

# get logging object
log = logging.getLogger('metadata')

# interesting file format info:
# http://www.danbbs.dk/~dino/whirlgif/gif87.html

class GIF(core.Image):

    def __init__(self,file):
        core.Image.__init__(self)
        self.mime = 'image/gif'

        try:
            header = struct.unpack('<6sHH', file.read(10))
        except struct.error:
            # EOF.
            raise core.ParseError()

        gifType, self.width, self.height = header

        if not gifType.startswith('GIF'):
            raise core.ParseError()

        self.type = gifType.lower()


Parser = GIF
