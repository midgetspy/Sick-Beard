# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xml.py - detect xml and fxd files
# -----------------------------------------------------------------------------
# $Id: xmlfile.py 4046 2009-05-22 20:22:29Z tack $
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
import sys
import logging
import xml.sax

# kaa.metadata imports
import kaa.metadata.core as core

# get logging object
log = logging.getLogger('metadata')

XML_TAG_INFO = {
    'image':  'Bins Image Description',
    'album':  'Bins Album Description',
    'freevo': 'Freevo XML Definition'
    }

class Identified:
    pass

class XML(core.Media):

    def __init__(self,file):
        ext = os.path.splitext(file.name)[1].lower()
        if not ext in ('.xml', '.fxd', '.html', '.htm'):
            raise core.ParseError()

        core.Media.__init__(self)

        self.mime  = 'text/xml'
        self.type  = ''

        if ext in ('.html', '.htm'):
            # just believe that it is a html file
            self.mime  = 'text/html'
            self.type  = 'HTML Document'
            return

        handler = xml.sax.ContentHandler()
        handler.startElement = self.startElement
        parser = xml.sax.make_parser()
        parser.setFeature('http://xml.org/sax/features/external-general-entities', False)
        parser.setContentHandler(handler)
        try:
            parser.parse(file)
        except Identified:
            pass
        except xml.sax.SAXParseException:
            raise core.ParseError()


    def startElement(self, name, attr):
        if name in XML_TAG_INFO:
            self.type = XML_TAG_INFO[name]
        else:
            self.type = 'XML file'
        raise Identified


Parser = XML
