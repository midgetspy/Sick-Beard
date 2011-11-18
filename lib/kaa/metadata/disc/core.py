# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py - basic class for any discs containing collections of media.
# -----------------------------------------------------------------------------
# $Id: core.py 3647 2008-10-25 19:52:16Z hmeine $
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

# python imports
import logging

# kaa imports
from kaa.metadata.core import ParseError, Collection, MEDIA_DISC
from kaa.metadata.video.core import VideoStream

# extra cdrom parser
import cdrom

# get logging object
log = logging.getLogger('metadata')

class Disc(Collection):

    _keys = Collection._keys + [ 'mixed', 'label' ]
    media = MEDIA_DISC

    def is_disc(self, device):
        (type, self.id) = cdrom.status(device, handle_mix=1)
        if type != 2:
            if type == 4:
                self.mixed = 1
                type = 1
            return type

        if cdrom.CREATE_MD5_ID:
            if len(self.id) == 32:
                self.label = ''
            else:
                self.label = self.id[32:]
        else:
            if len(self.id) == 16:
                self.label = ''
            else:
                self.label = self.id[16:]

        return type
