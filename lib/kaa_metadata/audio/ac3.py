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
import core
from ..exceptions import *

# http://www.atsc.org/standards/a_52a.pdf
# fscod: Sample rate code, 2 bits
#  00  48
#  01  44.1
#  10  32
#  11  reserved

FSCOD = [48000, 44100, 32000, 0]

# bsmod: Bit stream mode, 3 bits
# bsmod acmod Type of Service
#  000  any main audio service: complete main (CM)
#  001  any main audio service: music and effects (ME)
#  010  any associated service: visually impaired (VI)
#  011  any associated service: hearing impaired (HI)
#  100  any associated service: dialogue (D)
#  101  any associated service: commentary (C)
#  110  any associated service: emergency (E)
#  111  001 associated service: voice over (VO)
#  111  010 - 111  main audio service: karaoke
#
# acmod: Audio coding mode, 3 bits
#  000  1+1 2 Ch1, Ch2
#  001  1/0 1 C
#  010  2/0 2 L, R
#  011  3/0 3 L, C, R
#  100  2/1 3 L, R, S
#  101  3/1 4 L, C, R, S
#  110  2/2 4 L, R, SL, SR
#  111  3/2 5 L, C, R, SL, SR

ACMOD = [('1+1', 2, 'Ch1, Ch2'),
         ('1/0', 1, 'C'),
         ('2/0', 2, 'L, R'),
         ('3/0', 3, 'L, C, R'),
         ('2/1', 3, 'L, R, S'),
         ('3/1', 4, 'L, C, R, S'),
         ('2/2', 4, 'L, R, SL, SR'),
         ('3/2', 5, 'L, C, R, SL, SR')]


# dsurmod: Dolby surround mode, 2 bits
#  00  not indicated
#  01  Not Dolby Surround encoded
#  10  Dolby Surround encoded
#  11  reserved
#
# lfeon: Low frequency effects channel on, 1 bit
# This bit has a value of 1 if the lfe (sub woofer) channel is on, and a
# value of 0 if the lfe channel is off.
#
# frmsizcod:
#  byte&0x3e = 0x00        \b, 32 kbit/s
#  byte&0x3e = 0x02        \b, 40 kbit/s
#  byte&0x3e = 0x04        \b, 48 kbit/s
#  byte&0x3e = 0x06        \b, 56 kbit/s
#  byte&0x3e = 0x08        \b, 64 kbit/s
#  byte&0x3e = 0x0a        \b, 80 kbit/s
#  byte&0x3e = 0x0c        \b, 96 kbit/s
#  byte&0x3e = 0x0e        \b, 112 kbit/s
#  byte&0x3e = 0x10        \b, 128 kbit/s
#  byte&0x3e = 0x12        \b, 160 kbit/s
#  byte&0x3e = 0x14        \b, 192 kbit/s
#  byte&0x3e = 0x16        \b, 224 kbit/s
#  byte&0x3e = 0x18        \b, 256 kbit/s
#  byte&0x3e = 0x1a        \b, 320 kbit/s
#  byte&0x3e = 0x1c        \b, 384 kbit/s
#  byte&0x3e = 0x1e        \b, 448 kbit/s
#  byte&0x3e = 0x20        \b, 512 kbit/s
#  byte&0x3e = 0x22        \b, 576 kbit/s
#  byte&0x3e = 0x24        \b, 640 kbit/s

FRMSIZCOD = [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192,
             224, 256, 320, 384, 448, 512, 576, 640]

class AC3(core.Music):
    def __init__(self,file):
        core.Music.__init__(self)
        if file.name.endswith('.ac3'):
            # when the ending is ac3, force the detection. It may not be
            # necessary the the header is at the beginning but in the first
            # 2000 bytes
            check_length = 1000
        else:
            check_length = 1
        for i in range(check_length):
            if file.read(2) == '\x0b\x77':
                break
        else:
            raise ParseError()

        info = struct.unpack('<HBBBB',file.read(6))
        self.samplerate = FSCOD[info[1] >> 6]
        self.bitrate = FRMSIZCOD[(info[1] & 0x3F) >> 1] * 1000
        bsmod = info[2] & 0x7
        channels = ACMOD[info[3] >> 5]
        acmod = info[3] >> 5
        self.channels = ACMOD[acmod][1]
        bits = 0
        if acmod & 0x01 and not acmod == 0x01:
            bits += 2
        if acmod & 0x04:
            bits += 2
        if acmod == 0x02:
            bits += 2

        # info is now 5 bits of info[3] and all bits of info[4] ( == 13 bits)
        # 'bits' bits (0-6) bits are information we don't need, after that,
        # the bit we need is lfeon.
        info = (((info[3] & 0x1F) << 8) + info[4])

        # now we create the mask we need (based on 'bits')
        # the bit number 13 - 'bits' is what we want to read
        for i in range(13 - bits - 1):
            info = info >> 1
        if info & 1:
            # LFE channel
            self.channels += 1

        file.seek(-1, 2)
        size = file.tell()
        self.length = size * 8.0 / self.bitrate
        self.codec = 0x2000 # fourcc code of ac3
        self.mime = 'audio/ac3'


Parser = AC3
