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


# http://www.ap.org/apserver/userguide/codes.htm

from struct import unpack
from ..strutils import str_to_unicode

mapping = {
    'by-line title': 'title',
    'headline': 'title',
    'keywords': 'keywords',
    'writer-editor': 'author',
    'credit': 'author',
    'by-line': 'author',
    'country/primary location name': 'country',
    'caption-abstract': 'description',
    'city': 'city',
    'sub-location': 'location'
}

# These names match the codes defined in ITPC's IIM record 2.
# copied from iptcinfo by Josh Carter, josh@multipart-mixed.com
c_datasets = {
  # 0: 'record version',    # skip -- binary data
  5: 'object name',
  7: 'edit status',
  8: 'editorial update',
  10: 'urgency',
  12: 'subject reference',
  15: 'category',
  20: 'supplemental category',
  22: 'fixture identifier',
  25: 'keywords',
  26: 'content location code',
  27: 'content location name',
  30: 'release date',
  35: 'release time',
  37: 'expiration date',
  38: 'expiration time',
  40: 'special instructions',
  42: 'action advised',
  45: 'reference service',
  47: 'reference date',
  50: 'reference number',
  55: 'date created',
  60: 'time created',
  62: 'digital creation date',
  63: 'digital creation time',
  65: 'originating program',
  70: 'program version',
  75: 'object cycle',
  80: 'by-line',
  85: 'by-line title',
  90: 'city',
  92: 'sub-location',
  95: 'province/state',
  100: 'country/primary location code',
  101: 'country/primary location name',
  103: 'original transmission reference',
  105: 'headline',
  110: 'credit',
  115: 'source',
  116: 'copyright notice',
  118: 'contact',
  120: 'caption-abstract',
  122: 'writer-editor',
#  125: 'rasterized caption', # unsupported (binary data)
  130: 'image type',
  131: 'image orientation',
  135: 'language identifier',
  200: 'custom1', # These are NOT STANDARD, but are used by
  201: 'custom2', # Fotostation. Use at your own risk. They're
  202: 'custom3', # here in case you need to store some special
  203: 'custom4', # stuff, but note that other programs won't
  204: 'custom5', # recognize them and may blow them away if
  205: 'custom6', # you open and re-save the file. (Except with
  206: 'custom7', # Fotostation, of course.)
  207: 'custom8',
  208: 'custom9',
  209: 'custom10',
  210: 'custom11',
  211: 'custom12',
  212: 'custom13',
  213: 'custom14',
  214: 'custom15',
  215: 'custom16',
  216: 'custom17',
  217: 'custom18',
  218: 'custom19',
  219: 'custom20',
}


def flatten(list):
    try:
        for i, val in list.items()[:]:
            if len(val) == 0:
                del list[i]
            elif i == 'keywords':
                list[i] = [x.strip(' \t\0\n\r') for x in val]
            else:
                list[i] = u' '.join(val).strip()
        return list
    except (ValueError, AttributeError, IndexError, KeyError):
        return []


def parseiptc(app):
    iptc = {}
    if app[:14] == "Photoshop 3.0\x00":
        app = app[14:]

    # parse the image resource block
    offset = 0
    data = None
    while app[offset:offset+4] == "8BIM":
        offset = offset + 4
        # resource code
        code = unpack("<H", app[offset:offset+2])[0]
        offset = offset + 2
        # resource name (usually empty)
        name_len = ord(app[offset])
        name = app[offset+1:offset+1+name_len]
        offset = 1 + offset + name_len
        if offset & 1:
            offset = offset + 1
        # resource data block
        size = unpack("<L", app[offset:offset+4])[0]
        offset = offset + 4
        if code == 0x0404:
            # 0x0404 contains IPTC/NAA data
            data = app[offset:offset+size]
            break
        offset = offset + size
        if offset & 1:
            offset = offset + 1
    if not data:
        return None

    offset = 0
    iptc = {}
    while 1:
        try:
            intro = ord(data[offset])
        except (ValueError, KeyError, IndexError):
            return flatten(iptc)
        if intro != 0x1c:
            return flatten(iptc)
        (tag, record, dataset, length) = unpack("!BBBH", data[offset:offset+5])
        val = str_to_unicode(data[offset+5:offset+length+5])
        offset += length + 5
        name = c_datasets.get(dataset)
        if not name:
            continue
        if iptc.has_key(name):
            iptc[name].append(val)
        else:
            iptc[name] = [val]
    return flatten(iptc)
