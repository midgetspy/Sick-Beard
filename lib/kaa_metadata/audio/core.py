# -*- coding: utf-8 -*-
# kaa-Metadata - Media Metadata for Python
#
# Copyright (C) 2003-2006 Thomas Schueppel <stain@acm.org>
# Copyright (C) 2003-2006 Dirk Meyer <dischi@freevo.org>
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

import sys
from ..core import Media, MEDIA_AUDIO

AUDIOCORE = ['channels', 'samplerate', 'length', 'encoder', 'codec', 'format',
             'samplebits', 'bitrate', 'fourcc', 'trackno', 'id', 'userdate',
             'enabled', 'default', 'codec_private']

MUSICCORE = ['trackof', 'album', 'genre', 'discs', 'thumbnail']


class Audio(Media):
    """
    Audio Tracks in a Multiplexed Container.
    """
    _keys = Media._keys + AUDIOCORE
    media = MEDIA_AUDIO


class Music(Audio):
    """
    Digital Music.
    """
    _keys = Audio._keys + MUSICCORE

    def _finalize(self):
        """
        Correct same data based on specific rules
        """
        Audio._finalize(self)
        if self.trackof:
            try:
                # XXX Why is this needed anyway?
                if int(self.trackno) < 10:
                    self.trackno = u'0%s' % int(self.trackno)
            except (AttributeError, ValueError):
                pass
