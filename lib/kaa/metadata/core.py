# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# core.py
# -----------------------------------------------------------------------------
# $Id: core.py 3659 2008-11-09 16:44:43Z dmeyer $
#
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------

# python imports
import re
import logging

# kaa imports
import kaa

import fourcc
import language

UNPRINTABLE_KEYS = [ 'thumbnail', 'url' ]

# media type definitions
MEDIA_AUDIO     = 'MEDIA_AUDIO'
MEDIA_VIDEO     = 'MEDIA_VIDEO'
MEDIA_IMAGE     = 'MEDIA_IMAGE'
MEDIA_AV        = 'MEDIA_AV'
MEDIA_SUBTITLE  = 'MEDIA_SUBTITLE'
MEDIA_CHAPTER   = 'MEDIA_CHAPTER'
MEDIA_DIRECTORY = 'MEDIA_DIRECTORY'
MEDIA_DISC      = 'MEDIA_DISC'
MEDIA_GAME      = 'MEDIA_GAME'


MEDIACORE = ['title', 'caption', 'comment', 'size', 'type', 'subtype', 'timestamp',
             'keywords', 'country', 'language', 'langcode', 'url', 'media', 'artist',
             'mime']

EXTENSION_DEVICE    = 'device'
EXTENSION_DIRECTORY = 'directory'
EXTENSION_STREAM    = 'stream'

# get logging object
log = logging.getLogger('metadata')


class ParseError:
    pass


class Media(object):
    media = None

    """
    Media is the base class to all Media Metadata Containers. It defines
    the basic structures that handle metadata. Media and its derivates
    contain a common set of metadata attributes that is listed in keys.
    Specific derivates contain additional keys to the dublin core set that is
    defined in Media.
    """
    _keys = MEDIACORE
    table_mapping = {}

    def __init__(self, hash=None):
        if hash is not None:
            # create Media based on dict
            for key, value in hash.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    value = [ Media(x) for x in value ]
                self._set(key, value)
            return

        self._keys = self._keys[:]
        self.tables = {}
        for key in self._keys:
            if not key == 'media':
                setattr(self, key, None)


    #
    # unicode and string convertion for debugging
    #

    def __unicode__(self):
        result = u''

        # print normal attributes
        lists = []
        for key in self._keys:
            value = getattr(self, key, None)
            if value == None or key == 'url':
                continue
            if isinstance(value, list):
                if value:
                    lists.append((key, value))
                continue
            if key in UNPRINTABLE_KEYS:
                value = '<unprintable data, size=%d>' % len(value)
            result += u'| %10s: %s\n' % (unicode(key), unicode(value))

        # print lists
        for key, l in lists:
            for n, item in enumerate(l):
                label = '+-- ' + key.rstrip('s').capitalize()
                if key not in ('tracks', 'subtitles', 'chapters'):
                    label += ' Track'
                result += u'%s #%d\n' % (label, n+1)
                result += '|    ' + re.sub(r'\n(.)', r'\n|    \1', unicode(item))

        # print tables
        if log.level >= 10:
            for name, table in self.tables.items():
                result += '+-- Table %s\n' % str(name)
                for key, value in table.items():
                    try:
                        value = unicode(value)
                        if len(value) > 50:
                            value = u'<unprintable data, size=%d>' % len(value)
                    except (UnicodeDecodeError, TypeError), e:
                        try:
                            value = u'<unprintable data, size=%d>' % len(value)
                        except AttributeError:
                            value = u'<unprintable data>'
                    result += u'|    | %s: %s\n' % (unicode(key), value)
        return result


    def __str__(self):
        return kaa.unicode_to_str(unicode(self))


    def __repr__(self):
        if hasattr(self, 'url'):
            return '<%s %s>' % (str(self.__class__)[8:-2], self.url)
        else:
            return '<%s>' % (str(self.__class__)[8:-2])


    #
    # internal functions
    #

    def _appendtable(self, name, hashmap):
        """
        Appends a tables of additional metadata to the Object.
        If such a table already exists, the given tables items are
        added to the existing one.
        """
        if not self.tables.has_key(name):
            self.tables[name] = hashmap
        else:
            # Append to the already existing table
            for k in hashmap.keys():
                self.tables[name][k] = hashmap[k]


    def _set(self, key, value):
        """
        Set key to value and add the key to the internal keys list if
        missing.
        """
        if value is None and getattr(self, key, None) is None:
            return
        if isinstance(value, str):
            value = kaa.str_to_unicode(value)
        setattr(self, key, value)
        if not key in self._keys:
            self._keys.append(key)


    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        # make sure all strings are unicode
        for key in self._keys:
            if key in UNPRINTABLE_KEYS:
                continue
            value = getattr(self, key)
            if value is None:
                continue
            if key == 'image':
                if isinstance(value, unicode):
                    setattr(self, key, kaa.unicode_to_str(value))
                continue
            if isinstance(value, str):
                setattr(self, key, kaa.str_to_unicode(value))
            if isinstance(value, unicode):
                setattr(self, key, value.strip().rstrip().replace(u'\0', u''))
            if isinstance(value, list) and value and isinstance(value[0], Media):
                for submenu in value:
                    submenu._finalize()

        # copy needed tags from tables
        for name, table in self.tables.items():
            mapping = self.table_mapping.get(name, {})
            for tag, attr in mapping.items():
                if self.get(attr):
                    continue
                value = table.get(tag, None)
                if value is not None:
                    if not isinstance(value, (str, unicode)):
                        value = kaa.str_to_unicode(str(value))
                    elif isinstance(value, str):
                        value = kaa.str_to_unicode(value)
                    value = value.strip().rstrip().replace(u'\0', u'')
                    setattr(self, attr, value)

        if 'fourcc' in self._keys and 'codec' in self._keys and self.codec is not None:
            # Codec may be a fourcc, in which case we resolve it to its actual
            # name and set the fourcc attribute.
            self.fourcc, self.codec = fourcc.resolve(self.codec)
        if 'language' in self._keys:
            self.langcode, self.language = language.resolve(self.language)


    #
    # data access
    #

    def __contains__(self, key):
        """
        Test if key exists in the dict
        """
        return hasattr(self, key)


    def get(self, attr, default = None):
        """
        Returns the given attribute. If the attribute is not set by
        the parser return 'default'.
        """
        return getattr(self, attr, default)


    def __getitem__(self, attr):
        """
        Get the value of the given attribute
        """
        return getattr(self, attr, None)


    def __setitem__(self, key, value):
        """
        Set the value of 'key' to 'value'
        """
        setattr(self, key, value)


    def has_key(self, key):
        """
        Check if the object has an attribute 'key'
        """
        return hasattr(self, key)


    def convert(self):
        """
        Convert Media to dict.
        """
        result = {}
        for k in self._keys:
            value = getattr(self, k, None)
            if isinstance(value, list) and value and isinstance(value[0], Media):
                value = [ x.convert() for x in value ]
            result[k] = value
        return result


    def keys(self):
        """
        Return all keys for the attributes set by the parser.
        """
        return self._keys


class Collection(Media):
    """
    Collection of Digial Media like CD, DVD, Directory, Playlist
    """
    _keys = Media._keys + [ 'id', 'tracks' ]

    def __init__(self):
        Media.__init__(self)
        self.tracks = []
