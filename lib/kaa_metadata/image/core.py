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

import os
import sys
import logging
import xml.sax
from ..core import Media, MEDIA_IMAGE
from ..exceptions import ParseError

# get logging object
log = logging.getLogger(__name__)

# attributes for image files
ATTRIBUTES = ['description', 'people', 'location', 'event', 'width', 'height',
              'thumbnail','software','hardware', 'dpi', 'city', 'rotation', 'author']


class BinsParser(xml.sax.ContentHandler):
    def __init__(self, filename):
        xml.sax.ContentHandler.__init__(self)
        self.mode = 0
        self.var = None
        self.dict = {}

        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        try:
            parser.parse(filename)
        except ParseError:
            pass
        except Exception, e:
            log.exception('bins parser')

    def items(self):
        return self.dict.items()

    def startElement(self, name, attr):
        if self.mode == 0:
            if name not in ['album', 'image']:
                raise ParseError
            self.mode = 1
        if self.mode == 2 and name == 'field':
            self.var = attr['name']
            self.chars = ''
        if self.mode == 1 and name == 'description':
            self.mode = 2

    def endElement(self, name):
        if self.mode == 2 and name == 'description':
            self.mode = 1
        if self.var:
            value = self.chars.strip()
            if value:
                self.dict[self.var] = value
            self.var = None

    def characters(self, c):
        if self.var:
            self.chars += c

class Image(Media):
    """
    Digital Images, Photos, Pictures.
    """

    _keys = Media._keys + ATTRIBUTES
    media = MEDIA_IMAGE

    def _finalize(self):
        """
        Add additional information and correct data.
        FIXME: parse_external_files here is very wrong
        """
        if self.url and self.url.startswith('file://'):
            self.parse_external_files(self.url[7:])
        Media._finalize(self)


    def parse_external_files(self, filename):
        """
        Parse external files like bins and .comments.
        """
        # Parse bins xml files
        binsxml = filename + '.xml'
        if os.path.isfile(binsxml):
            bins = BinsParser(binsxml)
            for key, value in bins.items():
                self._set(key, value)
        # FIXME: this doesn't work anymore
        comment_file = os.path.join(os.path.dirname(filename), '.comments',
                                    os.path.basename(filename) + '.xml')
        if not os.path.isfile(comment_file) or 1:
            return
        # FIXME: replace kaa.xml stuff with sax or minidom
        doc = xml.Document(comment_file, 'Comment')
        for child in doc.children:
            if child.name == 'Place':
                self.location = child.content
            if child.name == 'Note':
                self.description = child.content
