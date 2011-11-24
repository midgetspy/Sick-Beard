# -*- coding: utf-8 -*-
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

__all__ = ['Parser']

import struct
import core
from ..exceptions import *

# ADTS Fixed header: these don't change from frame to frame
#
# syncword                       12        always: '111111111111'
# ID                              1        0: MPEG-4, 1: MPEG-2
# layer                           2        always: '00'
# protection_absent               1

# profile                         2
# sampling_frequency_index        4
# private_bit                     1
# channel_configuration           3

# original/copy                   1
# home                            1
#
# ADTS Variable header: these can change from frame to frame
#
# copyright_identification_bit    1
# copyright_identification_start  1
# aac_frame_length               13  length of the frame including header (in bytes)
# adts_buffer_fullness           11  0x7FF indicates VBR
# no_raw_data_blocks_in_frame     2
#
# ADTS Error check
#
# crc_check                      16  only if protection_absent == 0
#
class ADTS(core.Music):
    def __init__(self,file):
        core.Music.__init__(self)
        if not file.name.endswith('aac'):
            # we have a bad detection here, so if the filename does
            # not match, we skip.
            raise ParseError()
        header = struct.unpack('>7B', file.read(7))
        if header[0] != 255 or (header[1] >> 4) != 15:
            raise ParseError()
        self.mime = 'audio/aac'

Parser = ADTS
