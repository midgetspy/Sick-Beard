# -*- coding: utf-8 -*-
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Richard Mottershead <richard.mottershead@v21net.co.uk>
# Maintainer:    Richard Mottershead <richard.mottershead@v21net.co.uk>
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

import logging
from ..exceptions import *
import core

# get logging object
log = logging.getLogger(__name__)

# interesting file format info:
# GameBoy Advance http://www.forums.emuita.it/index.php?showtopic=67255

GBA_LOGOCODE = '\x24\xff\xae\x51\x69\x9a\xa2\x21\x3d\x84\x82\x0a\x84\xe4\x09\xad\x11\x24\x8b\x98\xc0\x81\x7f\x21\xa3\x52\xbe\x19\x93\x09\xce\x20\x10\x46\x4a\x4a\xf8\x27\x31\xec\x58\xc7\xe8\x33\x82\xe3\xce\xbf\x85\xf4\xdf\x94\xce\x4b\x09\xc1\x94\x56\x8a\xc0\x13\x72\xa7\xfc\x9f\x84\x4d\x73\xa3\xca\x9a\x61\x58\x97\xa3\x27\xfc\x03\x98\x76\x23\x1d\xc7\x61\x03\x04\xae\x56\xbf\x38\x84\x00\x40\xa7\x0e\xfd\xff\x52\xfe\x03\x6f\x95\x30\xf1\x97\xfb\xc0\x85\x60\xd6\x80\x25\xa9\x63\xbe\x03\x01\x4e\x38\xe2\xf9\xa2\x34\xff\xbb\x3e\x03\x44\x78\x00\x90\xcb\x88\x11\x3a\x94\x65\xc0\x7c\x63\x87\xf0\x3c\xaf\xd6\x25\xe4\x8b\x38\x0a\xac\x72\x21\xd4\xf8\x07'

GB_LOGOCODE = '\xCE\xED\x66\x66\xCC\x0D\x00\x0B\x03\x73\x00\x83\x00\x0C\x00\x0D\x00\x08\x11\x1F\x88\x89\x00\x0E\xDC\xCC\x6E\xE6\xDD\xDD\xD9\x99\xBB\xBB\x67\x63\x6E\x0E\xEC\xCC\xDD\xDC\x99\x9F\xBB\xB9\x33\x3E'

class Gameboy(core.Game):

    def __init__(self,file):
        core.Game.__init__(self)

        # Determine if the ROM is a Gameboy Advance ROM.
        # Compare the Logo Code. All GBA Roms have this code.
        file.seek(4)
        if file.read(156) != GBA_LOGOCODE:

            # Determine if the ROM is a Standard Gameboy ROM
            # Compare the Logo Code. All GB Roms have this code.
            file.seek (260)
            if file.read(len(GB_LOGOCODE)) != GB_LOGOCODE:
                raise ParseError()

            # Retrieve the ROM Title
            game_title = file.read(15)
            self.title = game_title

            # Retrieve the Rom Type (GB Colour or GB)j
            if file.read(1) == '\x80':
                self.mime = 'games/gbc'
                self.type = 'GameBoyColour game'
            else:
                self.mime = 'games/gb'
                self.type = 'GameBoy game'

        else:

            self.mime = 'games/gba'
            self.type = 'GameBoyAdvance game'

            # Retrieve the ROM Title
            game_title = file.read(12)
            self.title = game_title

            # Retrieve the Game Code
            game_code = file.read(4)

            # Retrieve the  Manufacturer Code
            maker_code = file.read(2)
            log.debug("MAKER CODE: %s" % maker_code)

            # Check that the Fized Value is 0x96, if not then error.
            if file.read(1) != '\x96':
                raise ParseError()


Parser = Gameboy
