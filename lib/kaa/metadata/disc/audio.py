# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# audio.py - support for audio cds
# -----------------------------------------------------------------------------
# $Id: audio.py 3621 2008-10-12 20:26:54Z dmeyer $
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
import logging

# kaa.metadata imports
import kaa.metadata
from kaa.metadata.audio.core import Music as AudioTrack

# kaa.metadata.disc imports
import core
import cdrom
import CDDB

# get logging object
log = logging.getLogger('metadata')


class AudioDisc(core.Disc):
    """
    Audio CD support. It provides a list of tracks and if on Internet
    connection is available it will use CDDB for the metadata.
    """
    def __init__(self,device):
        core.Disc.__init__(self)
        self.offset = 0
        # check disc
        if self.is_disc(device) != 1:
            raise core.ParseError()

        self.query(device)
        self.mime = 'audio/cd'
        self.type = 'CD'
        self.subtype = 'audio'


    def query(self, device):

        cdromfd = cdrom.audiocd_open(device)
        disc_id = cdrom.audiocd_id(cdromfd)

        if kaa.metadata.USE_NETWORK:
            try:
                (query_stat, query_info) = CDDB.query(disc_id)
            except Exception, e:
                # Oops no connection
                query_stat = 404
        else:
            query_stat = 404

        if query_stat == 210 or query_stat == 211:
            # set this to success
            query_stat = 200

            for i in query_info:
                if i['title'] != i['title'].upper():
                    query_info = i
                    break
            else:
                query_info = query_info[0]

        elif query_stat != 200:
            log.error("failure getting disc info, status %i" % query_stat)

        if query_stat == 200:
            qi = query_info['title'].split('/')
            self.artist = qi[0].strip()
            self.title = qi[1].strip()
            for type in ('title', 'artist'):
                if getattr(self, type) and \
                       getattr(self, type)[0] in ('"', '\'') \
                       and getattr(self, type)[-1] in ('"', '\''):
                    setattr(self, type, getattr(self, type)[1:-1])
            (read_stat, read_info) = CDDB.read(query_info['category'],
                                               query_info['disc_id'])
            # id = disc_id + number of tracks
            #self.id = '%s_%s' % (query_info['disc_id'], disc_id[1])

            if read_stat == 210:
                self.year = read_info['DYEAR']

                for i in range(0, disc_id[1]):
                    mi = AudioTrack()
                    mi.title = read_info['TTITLE' + `i`]
                    mi.album = self.title
                    mi.artist = self.artist
                    mi.genre = query_info['category']
                    mi.year = self.year
                    mi.codec = 'PCM'
                    mi.samplerate = 44100
                    mi.trackno = i+1
                    mi.trackof = disc_id[1]
                    self.tracks.append(mi)
                    for type in ('title', 'album', 'artist', 'genre'):
                        if getattr(mi, type) and \
                               getattr(mi, type)[0] in ('"', '\'') \
                           and getattr(mi, type)[-1] in ('"', '\''):
                            setattr(mi, type, getattr(mi, type)[1:-1])
            else:
                log.error("failure getting track info, status: %i" % read_stat)
                # set query_stat to somthing != 200
                query_stat = 400


        if query_stat != 200:
            log.error("failure getting disc info, status %i" % query_stat)
            self.no_caching = 1
            for i in range(0, disc_id[1]):
                mi = AudioTrack()
                mi.title = 'Track %s' % (i+1)
                mi.codec = 'PCM'
                mi.samplerate = 44100
                mi.trackno = i+1
                mi.trackof = disc_id[1]
                self.tracks.append(mi)


        # read the tracks to generate the title list
        (first, last) = cdrom.audiocd_toc_header(cdromfd)

        lmin = 0
        lsec = 0

        num = 0
        for i in range(first, last + 2):
            if i == last + 1:
                min, sec, frames = cdrom.audiocd_leadout(cdromfd)
            else:
                min, sec, frames = cdrom.audiocd_toc_entry(cdromfd, i)
            if num:
                self.tracks[num-1].length = (min-lmin)*60 + (sec-lsec)
            num += 1
            lmin, lsec = min, sec

        # correct bad titles for the tracks, containing also the artist
        for t in self.tracks:
            if not self.artist or not t.title.startswith(self.artist):
                break
        else:
            for t in self.tracks:
                t.title = t.title[len(self.artist):].lstrip('/ \t-_')

        # correct bad titles for the tracks, containing also the title
        for t in self.tracks:
            if not self.title or not t.title.startswith(self.title):
                break
        else:
            for t in self.tracks:
                t.title = t.title[len(self.title):].lstrip('/ \t-_')

        cdromfd.close()


Parser = AudioDisc
