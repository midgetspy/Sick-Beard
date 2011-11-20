# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# data.py - info about a normal data disc
# -----------------------------------------------------------------------------
# $Id: data.py 2581 2007-03-22 14:16:50Z tack $
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

# kaa.metadata.disc imports
import core

class DataDisc(core.Disc):
    def __init__(self,device):
        core.Disc.__init__(self)
        if self.is_disc(device) != 2:
            raise core.ParseError()
        self.offset = 0
        self.mime = 'unknown/unknown'
        self.type = 'CD'
        self.subtype = 'data'


Parser = DataDisc
