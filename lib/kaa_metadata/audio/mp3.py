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

__all__ = ['Parser']

import re
import sys
import logging
import struct
from ..strutils import str_to_unicode
import core
import ID3 as ID3
from eyeD3 import tag as eyeD3_tag
from eyeD3 import frames as eyeD3_frames
from ..exceptions import *


# get logging object
log = logging.getLogger(__name__)

# http://www.omniscia.org/~vivake/python/MP3Info.py

MP3_INFO_TABLE = { "LINK": "link",
                   "TALB": "album",
                   "TCOM": "composer",
                   "TCOP": "copyright",
                   "TDOR": "release",
                   "TYER": "userdate",
                   "TEXT": "text",
                   "TIT2": "title",
                   "TLAN": "language",
                   "TLEN": "length",
                   "TMED": "media_type",
                   "TPE1": "artist",
                   "TPE2": "artist",
                   "TRCK": "trackno",
                   "TPOS": "discs",
                   "TPUB": "publisher"}

_bitrates = [
   [ # MPEG-2 & 2.5
   [0,32,48,56, 64, 80, 96,112,128,144,160,176,192,224,256,None], # Layer 1
   [0, 8,16,24, 32, 40, 48, 56, 64, 80, 96,112,128,144,160,None], # Layer 2
   [0, 8,16,24, 32, 40, 48, 56, 64, 80, 96,112,128,144,160,None]  # Layer 3
   ],

   [ # MPEG-1
   [0,32,64,96,128,160,192,224,256,288,320,352,384,416,448,None], # Layer 1
   [0,32,48,56, 64, 80, 96,112,128,160,192,224,256,320,384,None], # Layer 2
   [0,32,40,48, 56, 64, 80, 96,112,128,160,192,224,256,320,None]  # Layer 3
   ]
   ]

_samplerates = [
   [11025, 12000, 8000,  None], # MPEG-2.5
   [None,  None,  None,  None], # reserved
   [22050, 24000, 16000, None], # MPEG-2
   [44100, 48000, 32000, None], # MPEG-1
   ]

_modes = ["stereo", "joint stereo", "dual channel", "mono"]

_MP3_HEADER_SEEK_LIMIT = 4096

class MP3(core.Music):

    fileName = str();
    fileSize = int();

    def __init__(self, file, tagVersion = eyeD3_tag.ID3_ANY_VERSION):
        core.Music.__init__(self)
        self.fileName = file.name;
        self.codec = 0x0055 # fourcc code of mp3
        self.mime = 'audio/mpeg'

        #if not eyeD3_tag.isMp3File(file.name):
        #   raise ParseError()

        id3 = None
        try:
            id3 = eyeD3_tag.Mp3AudioFile(file.name)
        except eyeD3_tag.InvalidAudioFormatException:
            # File is not an MP3
            raise ParseError()
        except eyeD3_tag.TagException:
            # The MP3 tag decoder crashed, assume the file is still
            # MP3 and try to play it anyway
            if log.level < 30:
                log.exception('mp3 tag parsing %s failed!' % file.name)
        except Exception:
            # The MP3 tag decoder crashed, assume the file is still
            # MP3 and try to play it anyway
            if log.level < 30:
                log.exception('mp3 tag parsing %s failed!' % file.name)

        if not id3:
            # let's take a look at the header
            s = file.read(4096)
            if not s[:3] == 'ID3':
                # no id3 tag header, not good
                if not re.compile(r'0*\xFF\xFB\xB0\x04$').search(s):
                    # again, not good
                    if not re.compile(r'0*\xFF\xFA\xB0\x04$').search(s):
                        # that's it, it is no mp3 at all
                        raise ParseError()

        try:
            if id3 and id3.tag:
                log.debug(id3.tag.frames)

                # Grip unicode bug workaround: Grip stores text data as UTF-8
                # and flags it as latin-1.  This workaround tries to decode
                # these strings as utf-8 instead.
                # http://sourceforge.net/tracker/index.php?func=detail&aid=1196919&group_id=3714&atid=103714
                for frame in id3.tag.frames['COMM']:
                    if "created by grip" not in frame.comment.lower():
                        continue
                    for frame in id3.tag.frames:
                        if hasattr(frame, "text") and isinstance(frame.text, unicode):
                            try:
                                frame.text = frame.text.encode('latin-1').decode('utf-8')
                            except UnicodeError:
                                pass

                for k, var in MP3_INFO_TABLE.items():
                    if id3.tag.frames[k]:
                        self._set(var,id3.tag.frames[k][0].text)
                if id3.tag.frames['APIC']:
                    pic = id3.tag.frames['APIC'][0]
                    if pic.imageData:
                        self.thumbnail = pic.imageData
                if id3.tag.getYear():
                    self.userdate = id3.tag.getYear()
                tab = {}
                for f in id3.tag.frames:
                    if f.__class__ is eyeD3_frames.TextFrame:
                        tab[f.header.id] = f.text
                    elif f.__class__ is eyeD3_frames.UserTextFrame:
                        #userTextFrames : debug: id  starts with _
                        self._set('_'+f.description,f.text)
                        tab['_'+f.description] = f.text
                    elif f.__class__ is eyeD3_frames.DateFrame:
                        tab[f.header.id] = f.date_str
                    elif f.__class__ is eyeD3_frames.CommentFrame:
                        tab[f.header.id] = f.comment
                        self.comment = str_to_unicode(f.comment)
                    elif f.__class__ is eyeD3_frames.URLFrame:
                        tab[f.header.id] = f.url
                    elif f.__class__ is eyeD3_frames.UserURLFrame:
                        tab[f.header.id] = f.url
                    elif f.__class__ is eyeD3_frames.ImageFrame:
                        tab[f.header.id] = f
                    else:
                        log.debug(f.__class__)
                self._appendtable('id3v2', tab)

                if id3.tag.frames['TCON']:
                    genre = None
                    tcon = id3.tag.frames['TCON'][0].text
                    # TODO: could handle id3v2 genre refinements.
                    try:
                        # Assume integer.
                        genre = int(tcon)
                    except ValueError:
                        # Nope, maybe it's in '(N)' format.
                        try:
                            genre = int(tcon[1:tcon.find(')')])
                        except ValueError:
                            # Nope.  Treat as a string.
                            self.genre = str_to_unicode(tcon)

                    if genre is not None:
                        try:
                            self.genre = ID3.GENRE_LIST[genre]
                        except KeyError:
                            # Numeric genre specified but not one of the known genres,
                            # use 'Unknown' as per ID3v1.
                            self.genre = u'Unknown'

                # and some tools store it as trackno/trackof in TRCK
                if not self.trackof and self.trackno and \
                       self.trackno.find('/') > 0:
                    self.trackof = self.trackno[self.trackno.find('/')+1:]
                    self.trackno = self.trackno[:self.trackno.find('/')]
            if id3:
                self.length = id3.getPlayTime()
        except Exception:
            if log.level < 30:
                log.exception('parse error')

        offset, header = self._find_header(file)
        if offset == -1 or header is None:
            return

        self._parse_header(header)

        if id3:
            # Note: information about variable bitrate or not should
            # be handled somehow.
            (vbr, self.bitrate) = id3.getBitRate()

    def _find_header(self, file):
        file.seek(0, 0)
        amount_read = 0

        # see if we get lucky with the first four bytes
        amt = 4

        while amount_read < _MP3_HEADER_SEEK_LIMIT:
            header = file.read(amt)
            if len(header) < amt:
                # awfully short file. just give up.
                return -1, None

            amount_read = amount_read + len(header)

            # on the next read, grab a lot more
            amt = 500

            # look for the sync byte
            offset = header.find(chr(255))
            if offset == -1:
                continue

            # looks good, make sure we have the next 3 bytes after this
            # because the header is 4 bytes including sync
            if offset + 4 > len(header):
                more = file.read(4)
                if len(more) < 4:
                    # end of file. can't find a header
                    return -1, None
                amount_read = amount_read + 4
                header = header + more

            # the sync flag is also in the next byte, the first 3 bits
            # must also be set
            if ord(header[offset+1]) >> 5 != 7:
                continue

            # ok, that's it, looks like we have the header
            return amount_read - len(header) + offset, header[offset:offset+4]

        # couldn't find the header
        return -1, None


    def _parse_header(self, header):
        # http://mpgedit.org/mpgedit/mpeg_format/MP3Format.html
        bytes = struct.unpack('>i', header)[0]
        mpeg_version = (bytes >> 19) & 3
        layer = (bytes >> 17) & 3
        bitrate = (bytes >> 12) & 15
        samplerate = (bytes >> 10) & 3
        mode = (bytes >> 6)  & 3

        if mpeg_version == 0:
            self.version = 2.5
        elif mpeg_version == 2:
            self.version = 2
        elif mpeg_version == 3:
            self.version = 1
        else:
            return

        if layer > 0:
            layer = 4 - layer
        else:
            return

        self.bitrate = _bitrates[mpeg_version & 1][layer - 1][bitrate]
        self.samplerate = _samplerates[mpeg_version][samplerate]

        if self.bitrate is None or self.samplerate is None:
            return

        self._set('mode', _modes[mode])


Parser = MP3
