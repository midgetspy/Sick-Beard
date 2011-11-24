# -*- coding: utf-8 -*-
# kaa-Metadata - Media Metadata for Python
# Copyright (C) 2003-2006 Thomas Schueppel, Dirk Meyer
#
# First Edition: Aubin Paul <aubin@outlyer.org>
# Maintainer:    Dirk Meyer <dischi@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# Based on a sample implementation posted to daap-dev mailing list by
# Bob Ippolito <bob@redivi.com>
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
import logging
import core
from ..exceptions import *

# get logging object
log = logging.getLogger(__name__)


FLAGS= CONTAINER, SKIPPER, TAGITEM, IGNORE= [2**_ for _ in xrange(4)]

# CONTAINER: datum contains other boxes
# SKIPPER: ignore first 4 bytes of datum
# TAGITEM: "official" tag item
CALLBACK= TAGITEM
FLAGS.append(CALLBACK)

TAGTYPES= (
    ('ftyp', TAGITEM),
    ('mvhd', 0),
    ('moov', CONTAINER),
    ('mdat', 0),
    ('udta', CONTAINER),
    ('meta', CONTAINER|SKIPPER),
    ('ilst', CONTAINER),
    ('\xa9ART', TAGITEM),
    ('\xa9nam', TAGITEM),
    ('\xa9too', TAGITEM),
    ('\xa9alb', TAGITEM),
    ('\xa9day', TAGITEM),
    ('\xa9gen', TAGITEM),
    ('\xa9wrt', TAGITEM),
    ('\xa9cmt', TAGITEM),
    ('trkn', TAGITEM),
    ('trak', CONTAINER),
    ('mdia', CONTAINER),
    ('mdhd', TAGITEM),
    ('minf', CONTAINER),
    ('dinf', CONTAINER),
    ('stbl', CONTAINER),
)

flagged= {}
for flag in FLAGS:
    flagged[flag]= frozenset(_[0] for _ in TAGTYPES if _[1] & flag)

def _analyse(fp, offset0, offset1):
    "Walk the atom tree in a mp4 file"
    offset= offset0
    while offset < offset1:
        fp.seek(offset)
        atomsize= struct.unpack("!i", fp.read(4))[0]
        atomtype= fp.read(4)
        if atomsize < 9:
            # This logic is not likely correct, but at least avoids
            # an exception from fp.read() below.
            break
        if atomtype in flagged[CONTAINER]:
            data= ''
            for reply in _analyse(fp, offset+(atomtype in flagged[SKIPPER] and 12 or 8),
                offset+atomsize):
                yield reply
        else:
            fp.seek(offset+8)
            if atomtype in flagged[TAGITEM]:
                data=fp.read(atomsize-8)
            else:
                data= fp.read(min(atomsize-8, 32))
            #print `atomtype`, `data`
        if not atomtype in flagged[IGNORE]: yield atomtype, atomsize, data
        offset+= atomsize

def mp4_atoms(fp):
    fp.seek(0,2)
    size=fp.tell()
    for atom in _analyse(fp, 0, size):
        yield atom

class M4ATags(dict):
    "An class reading .m4a tags"
    convtag= {
        'ftyp': 'FileType',
        'trkn': 'Track',
        'length': 'Length',
        'samplerate': 'SampleRate',
        '\xa9ART': 'Artist',
        '\xa9nam': 'Title',
        '\xa9alb': 'Album',
        '\xa9day': 'Year',
        '\xa9gen': 'Genre',
        '\xa9cmt': 'Comment',
        '\xa9wrt': 'Writer',
        '\xa9too': 'Tool',
    }
    def __init__(self, fp):
        super(dict, self).__init__()
        self['FileType'] = 'unknown'
        fp.seek(0,0)
        try:
            size= struct.unpack("!i", fp.read(4))[0]
        except struct.error:
            # EOF.
            return
        type= fp.read(4)
        #check for ftyp identification
        if type == 'ftyp':
            for atomtype, atomsize, atomdata in mp4_atoms(fp):
                self.atom2tag(atomtype, atomdata)

    def atom2tag(self, atomtype, atomdata):
        "Insert items using descriptive key instead of atomtype"
        if atomtype.find('\xa9',0,4) != -1:
            key= self.convtag[atomtype]
            self[key]= atomdata[16:].decode("utf-8")
        elif atomtype == 'mdhd':
            if ord(atomdata[0]) == 1:
                #if version is 1 then date and duration values are 8 bytes in length
                timescale= struct.unpack("!Q",atomdata[20:24])[0]
                duration= struct.unpack("!Q",atomdata[24:30])[0]
            else:
                timescale= struct.unpack("!i",atomdata[12:16])[0]
                duration= struct.unpack("!i",atomdata[16:20])[0]
            self[self.convtag['length']]= duration/timescale
            self[self.convtag['samplerate']]= timescale
        elif atomtype == 'trkn':
            self[self.convtag[atomtype]]= struct.unpack("!i",atomdata[16:20])[0]
        elif atomtype == 'ftyp':
            self[self.convtag[atomtype]]= atomdata[8:12].decode("utf-8")


class Mpeg4Audio(core.Music):

    def __init__(self, file):
        core.Music.__init__(self)
        tags = M4ATags(file)
        if tags.get('FileType') != 'M4A ':
            raise ParseError()

        self.valid = True
        self.mime = 'audio/mp4'
        self.filename = getattr(file, 'name', None)
        # Initialize core attributes from available tag values.
        self.title = tags.get('Title')
        self.artist = tags.get('Artist')
        self.album = tags.get('Album')
        self.trackno = tags.get('Track')
        self.year = tags.get('Year')
        self.encoder = tags.get('Tool')
        self.length = tags.get('Length')
        self.samplerate = tags.get('SampleRate')

Parser = Mpeg4Audio
