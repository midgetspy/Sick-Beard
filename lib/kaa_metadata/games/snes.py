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
import sys
from struct import unpack
from re import match
from ..exceptions import *
import core

# get logging object
log = logging.getLogger(__name__)

# interesting file format info:
# http://www.classicgaming.com/epr/super/sneskart.html#embededcartridge

# Used to detect the internal rome information, as described in
# 'SNESKART.DOC v1.3'
snesromFileOffset = [33216, 32704, 65472, 65984]

#most of the code is imported from the old snesitem.py.

class SNES(core.Game):

    def __init__(self,file):
        core.Game.__init__(self)

        self.mime = 'games/snes'
        self.type = 'SuperNintendo game'

        for offset in snesromFileOffset:
            log.debug('Checking for rom header at offset: %d' % offset)
            file.seek(offset)
            romHeader = file.read(32)
            try:
                (romName, romHL, rom_type, romROM, romSRAM, romCountry,
                 romLic, romVer, romICHK, romCHK) = \
                 unpack('21sBBcccccHH', romHeader)
            except Exception, e:
                continue

            if not rom_type in [0, 1, 2, 3, 4, 5, 19, 227, 246]:
                # invalid acording to the doc at www.classicgaming.com
                continue

            if not match('[a-zA-Z0-9 ]{21}', romName):
                # FIXME: bad hack, but it shoudl work. If not, send some
                # rom files to me. Without that many normal files are
                # detect as ROM
                continue

            log.debug('ROM NAME: "%s"' % romName)
            # Break now if CHECKSUM is OK
            if (romICHK | romCHK) == 0xFFFF:
                log.debug('SNES rom header detected at offset : %d!!!!' % offset)
                break
            # Bad Checksum, ignore for now
            break

        else:
            # not detected as rom
            raise ParseError()
        self.title = romName.strip()

Parser = SNES
