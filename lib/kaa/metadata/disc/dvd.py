# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# dvdinfo.py - parse dvd title structure
# -----------------------------------------------------------------------------
# $Id: dvd.py 3621 2008-10-12 20:26:54Z dmeyer $
#
# TODO: update the ifomodule and remove the lsdvd parser
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

# python imports
import os
import logging
import glob

# kaa.metadata imports
import kaa.metadata.video.core as video
import kaa.metadata.audio.core as audio

# kaa.metadata.disc imports
import core
try:
    import _ifoparser
except ImportError:
    _ifoparser = None

# get logging object
log = logging.getLogger('metadata')

_video_height = (480, 576, 0, 576)
_video_width  = (720, 704, 352, 352)
_video_fps    = (0, 25.00, 0, 29.97)
_video_format = ('NTSC', 'PAL')
_video_aspect = (4.0 / 3, 16.0 / 9, 1.0, 16.0 / 9)

class DVDVideo(video.VideoStream):
    def __init__(self, data):
        video.VideoStream.__init__(self)
        self.length = data[0]
        self.fps    = _video_fps[data[1]]
        self.format = _video_format[data[2]]
        self.aspect = _video_aspect[data[3]]
        self.width  = _video_width[data[4]]
        self.height = _video_height[data[5]]
        self.codec  = 'MP2V'


class DVDAudio(audio.Audio):

    _keys = audio.Audio._keys

    def __init__(self, info):
        audio.Audio.__init__(self)
        self.id, self.language, self.codec, self.channels, self.samplerate = info


class DVDTitle(video.AVContainer):

    _keys = video.AVContainer._keys + [ 'angles' ]

    def __init__(self, info):
        video.AVContainer.__init__(self)
        self.chapters = []
        pos = 0
        for length in info[0]:
            chapter = video.Chapter()
            chapter.pos = pos
            pos += length
            self.chapters.append(chapter)

        self.angles = info[1]

        self.mime = 'video/mpeg'
        self.video.append(DVDVideo(info[2:8]))
        self.length = self.video[0].length

        for a in info[-2]:
            self.audio.append(DVDAudio(a))

        for id, lang in info[-1]:
            sub = video.Subtitle(lang)
            sub.id = id
            self.subtitles.append(sub)


class DVDInfo(core.Disc):
    """
    DVD parser for DVD discs, DVD iso files and hard-disc and DVD
    directory structures with a VIDEO_TS folder.
    """
    _keys = core.Disc._keys + [ 'length' ]

    def __init__(self, device):
        core.Disc.__init__(self)
        self.offset = 0

        if isinstance(device, file):
            self.parseDVDiso(device)
        elif os.path.isdir(device):
            self.parseDVDdir(device)
        else:
            self.parseDisc(device)

        self.length = 0
        first       = 0

        for t in self.tracks:
            self.length += t.length
            if not first:
                first = t.length

        if self.length/len(self.tracks) == first:
            # badly mastered dvd
            self.length = first

        self.mime    = 'video/dvd'
        self.type    = 'DVD'
        self.subtype = 'video'


    def _parse(self, device):
        if not _ifoparser:
            log.debug("kaa.metadata not compiled with DVD support")
            raise core.ParseError()
        info = _ifoparser.parse(device)
        if not info:
            raise core.ParseError()
        for pos, title in enumerate(info):
            ti = DVDTitle(title)
            ti.trackno = pos + 1
            ti.trackof = len(info)
            self.tracks.append(ti)


    def parseDVDdir(self, dirname):
        def iglob(path, ifile):
            # Case insensitive glob to find video_ts dir/file.  Python 2.5 has
            # glob.iglob but this doesn't exist in 2.4.
            file_glob = ''.join([ '[%s%s]' % (c, c.upper()) for c in ifile ])
            return glob.glob(os.path.join(path, file_glob))

        if True not in [ os.path.isdir(x) for x in iglob(dirname, 'video_ts') ] + \
                       [ os.path.isfile(x) for x in iglob(dirname, 'video_ts.vob') ]:
            raise core.ParseError()

        # OK, try libdvdread
        self._parse(dirname)
        return 1


    def parseDisc(self, device):
        if self.is_disc(device) != 2:
            raise core.ParseError()

        # brute force reading of the device to find out if it is a DVD
        f = open(device,'rb')
        f.seek(32768, 0)
        buffer = f.read(60000)

        if buffer.find('UDF') == -1:
            f.close()
            raise core.ParseError()

        # seems to be a DVD, read a little bit more
        buffer += f.read(550000)
        f.close()

        if buffer.find('VIDEO_TS') == -1 and \
               buffer.find('VIDEO_TS.IFO') == -1 and \
               buffer.find('OSTA UDF Compliant') == -1:
            raise core.ParseError()

        # OK, try libdvdread
        self._parse(device)


    def parseDVDiso(self, f):
        # brute force reading of the device to find out if it is a DVD
        f.seek(32768, 0)
        buffer = f.read(60000)

        if buffer.find('UDF') == -1:
            raise core.ParseError()

        # seems to be a DVD, read a little bit more
        buffer += f.read(550000)

        if buffer.find('VIDEO_TS') == -1 and \
               buffer.find('VIDEO_TS.IFO') == -1 and \
               buffer.find('OSTA UDF Compliant') == -1:
            raise core.ParseError()

        # OK, try libdvdread
        self._parse(f.name)


Parser = DVDInfo
