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
from zope.interface import classImplements

from storm.info import ObjectInfo
from storm.store import EmptyResultSet, ResultSet
from storm.zope.interfaces import IResultSet, ISQLObjectResultSet
from storm import sqlobject as storm_sqlobject


classImplements(storm_sqlobject.SQLObjectResultSet, ISQLObjectResultSet)
classImplements(ResultSet, IResultSet)
classImplements(EmptyResultSet, IResultSet)

try:
    from zope.security.checker import NoProxy, BasicTypes, _available_by_default
except ImportError:
    # We don't have zope.security installed.
    pass
else:
    # The following is required for storm.info.get_obj_info() to have
    # access to a proxied object which is already in the store (IOW, has
    # the object info set already).  With this, Storm is able to
    # gracefully handle situations when a proxied object is passed to a
    # Store.
    _available_by_default.append("__storm_object_info__")
    BasicTypes[ObjectInfo] = NoProxy
