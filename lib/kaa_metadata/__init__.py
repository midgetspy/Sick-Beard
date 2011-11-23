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

import mimetypes
import os
import sys
from exceptions import *

PARSERS = [('audio.mp3', ['audio/mpeg'], ['mp3']),
           ('audio.ac3', ['audio/ac3'], ['ac3']),
           ('audio.adts', ['application/adts'], ['aac']),
           ('audio.m4a', ['audio/m4a'], ['m4a']),
           ('audio.ogg', ['application/ogg'], ['ogg']),
           ('audio.pcm', ['application/pcm'], ['aif', 'voc', 'au']),
           ('video.asf', ['video/asf'], ['asf', 'wmv', 'wma']),
           ('video.flv', ['video/flv'], ['flv']),
           ('video.mkv', ['video/x-matroska', 'audio/x-matroska', 'application/mkv'], ['mkv', 'mka', 'webm']),
           ('video.mp4', ['video/quicktime'], ['mov', 'qt', 'mp4', 'mp4a', '3gp', '3gp2', 'mk2']),
           ('video.mpeg', ['video/mpeg'], ['mpeg', 'mpg', 'mp4', 'ts']),
           ('video.ogm', ['application/ogg'], ['ogm', 'ogg']),
           ('video.real', ['video/real'], ['rm', 'ra', 'ram']),
           ('video.riff', ['video/avi'], ['wav', 'avi']),
           ('image.bmp', ['image/bmp'], ['bmp']),
           ('image.gif', ['image/gif'], ['gif']),
           ('image.jpg', ['image/jpeg'], ['jpg', 'jpeg']),
           ('image.png', ['image/png'], ['png']),
           ('image.tiff', ['image/tiff'], ['tif', 'tiff']),
           ('games.gameboy', ['games/gameboy'], ['gba', 'gb', 'gbc']),
           ('games.snes', ['games/snes'], ['smc', 'sfc', 'fig']),
           ('audio.flac', ['application/flac'], ['flac'])]


def parse(path):
    if not os.path.isfile(path):
        raise ValueError('Invalid path')
    extension = os.path.splitext(path)[1][1:]
    mimetype = mimetypes.guess_type(path)[0]
    parser_ext = None
    parser_mime = None
    for (parser_name, parser_mimetypes, parser_extensions) in PARSERS:
        if mimetype in parser_mimetypes:
            parser_mime = parser_name
        if extension in parser_extensions:
            parser_ext = parser_name
    parser = parser_ext or parser_mime
    if not parser:
        raise NoParserError()
    mod = getattr(__import__(parser, globals=globals(), locals=locals(), fromlist=[], level=-1), parser.split('.')[1])
    with open(path, 'rb') as f:
        p = mod.Parser(f)
    return p
