#
# Copyright (c) 2008 Canonical
#
# Written by James Henstridge <jamesh@canonical.com>
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

"""Support for configuration and management of Storm stores in a Django app."""

__all__ = ["ensure_stores_configured", "get_store", "get_store_uri"]


from storm.zope.zstorm import global_zstorm

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def configure_stores(settings):
    if not hasattr(settings, "STORM_STORES"):
        raise ImproperlyConfigured(
            "You need to specify STORM_STORES in your Django settings file.")

    for name, uri in settings.STORM_STORES.iteritems():
        global_zstorm.set_default_uri(name, uri)


have_configured_stores = False


def ensure_stores_configured():
    global have_configured_stores
    if not have_configured_stores:
        configure_stores(settings)
        have_configured_stores = True


def get_store(name):
    # Make sure that stores have been configured.
    ensure_stores_configured()

    return global_zstorm.get(name)


def get_store_uri(name):
    ensure_stores_configured()
    return global_zstorm.get_default_uris()[name]
