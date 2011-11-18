# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# version.py - version handling for kaa modules
# -----------------------------------------------------------------------------
# $Id: version.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# Copyright 2005-2009 Dirk Meyer, Jason Tackaberry
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
import math

class Version(object):
    """
    Version information for kaa modules.
    """
    def __init__(self, version):
        """
        Set internal version as string.
        """
        self.version = str(version)

    def __str__(self):
        """
        Convert to string.
        """
        return self.version

    def __float__(self):
        """
        Convert to float for comparison.
        """
        version = 0
        for pos, val in enumerate(self.version.split('.')):
            version += int(val) * (float(1) / math.pow(100, pos))
        return version

    def __cmp__(self, obj):
        """
        Compare two version.
        """
        if not isinstance(obj, Version):
            obj = Version(obj)
        return cmp(float(self), float(obj))
