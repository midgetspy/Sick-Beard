#
# Copyright (c) 2006, 2007 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Storm Object Relational Mapper.
#
# Storm is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Storm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os


# Use a 4-digit version for development versions with 99 as the final version.
# For example, if 0.15 is the currently released version of Storm, the
# development version should be version 0.15.0.99.  This will make it obvious
# that this isn't the 0.15 release version while also allowing us to release
# an 0.15.1 if need be.  Release versions should use 2-digit version numbers,
# with 0.16 being the next release version in this example.
version = "0.16.0"
version_info = tuple([int(x) for x in version.split(".")])


class UndefType(object):

    def __repr__(self):
        return "Undef"

    def __reduce__(self):
        return "Undef"


Undef = UndefType()


# C extensions are enabled by default.  They are not used if the
# STORM_CEXTENSIONS environment variable is set to '0'.  If they can't be
# imported Storm will automatically use Python versions of the optimized code
# in the C extension.
has_cextensions = False
if os.environ.get("STORM_CEXTENSIONS") != "0":
    try:
        from storm import cextensions
        has_cextensions = True
    except ImportError, e:
        if "cextensions" not in str(e):
           raise
