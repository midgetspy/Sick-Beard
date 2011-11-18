# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xmlutils.py - some classes helping dealing with xml files
# -----------------------------------------------------------------------------
# $Id: xmlutils.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# Copyright 2007-2009 Dirk Meyer, Jason Tackaberry
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

"""
This module provides a simple SAX handler with an interface similar to a pull
parser and Wrapper around xml.mindom for easier parsing of simple configuration
files or fxd files for Freevo. The wrapper can not handle complex XML structures
and supports only one text element inside an element. The API is wrapped
to match the kaa coding style.

The logic and some functions are copied from xml.dom.minidom.
"""

__all__ = [ 'create' ]

# python imports
import os
import codecs

# python xml import
try:
    import xml.sax
    import xml.dom.minidom
except ImportError, e:
    # Small hack before the next release. FIXME: this should be
    # removed for future versions again.
    print 'Error: detected files from previous kaa.base version!'
    print 'Please reinstall kaa by deleting all \'build\' subdirs'
    print 'for all kaa source modules and delete the kaa directory'
    print 'in the site-package directory'
    raise e

# we can't use cStringIO since it doesn't support Unicode strings
from StringIO import StringIO

def _write_data(writer, data):
    """
    Writes datachars to writer.
    """
    data = data.replace("&", "&amp;").replace("<", "&lt;")
    data = data.replace("\"", "&quot;").replace(">", "&gt;")
    writer.write(data)


class Node(object):
    """
    Wrapper around a xml.dom.Element
    """
    def __init__(self, node):
        self.minidom = node

    def __iter__(self):
        """
        Iterate through all child elements, skipping text nodes
        """
        for n in self.minidom.childNodes:
            if isinstance(n, xml.dom.minidom.Element):
                yield Node(n)

    def __getattr__(self, attr):
        """
        Magic function to return an XML attribute or a child with the
        given name. Check for minus/underscore conversion.
        """
        value = self.minidom.getAttribute(attr)
        if value:
            return value
        for child in self:
            if child.nodename == attr:
                return child
        if attr.find('_') >= 0:
            return getattr(self, attr.replace('_', '-'))

    @property
    def nodename(self):
        return self.minidom.nodeName

    @property
    def _minidom_document(self):
        node = self.minidom
        while node.parentNode:
            node = node.parentNode
        return node

    def _get_content(self):
        if len(self.minidom.childNodes):
            return self.minidom.childNodes[0].data
        return u''

    def _set_content(self, value):
        if not isinstance(value, (unicode, str)):
            value = str(value)
        node = self._minidom_document.createTextNode(value)
        self.minidom.appendChild(node)

    # we can not use the property from util here because this file is
    # needed by distribution and utils has many dependencies including
    # the mainloop that won't work in a non-installed version
    content = property(_get_content, _set_content, None, 'cdata content')

    def add_child(self, name, content=None, **attributes):
        """
        Add a child to the node.

        @param name: child name
        @param content: child text content
        @param attributes: node attributes
        @returns: new Node
        """
        node = self._minidom_document.createElement(name)
        self.minidom.appendChild(node)
        node = Node(node)
        if content is not None:
            node.content = content
        for key, value in attributes.items():
            if not isinstance(value, (unicode, str)):
                value = str(value)
            node.minidom.setAttribute(key, value)
        return node

    def writexml(self, writer, indent="", addindent="", newl=""):
        """
        Write the node and all children

        @param indent: current indentation
        @param addindent: indentation to add to higher levels
        @param newl: newline string
        """
        writer.write(indent+"<" + self.minidom.tagName)
        # write attributes
        attrs = self.minidom.attributes
        a_names = attrs.keys()
        a_names.sort()
        for a_name in a_names:
            writer.write(" %s=\"" % a_name)
            _write_data(writer, attrs[a_name].value)
            writer.write("\"")
        if len(self.minidom.childNodes) == 1 and \
           self.minidom.childNodes[0].nodeType == self.minidom.TEXT_NODE:
            # only a text node
            writer.write(">")
            _write_data(writer, self.minidom.childNodes[0].data)
            writer.write("</%s>%s" % (self.minidom.tagName,newl))
        elif self.minidom.childNodes:
            # node with children
            writer.write(">%s"%(newl))
            for node in self:
                node.writexml(writer,indent+addindent,addindent,newl)
            writer.write("%s</%s>%s" % (indent,self.minidom.tagName,newl))
        else:
            # no children
            writer.write("/>%s"%(newl))

    def toxml(self):
        """
        Convert Node into an XML string with UTF-8 encoding
        """
        writer = codecs.lookup('utf8')[3](StringIO())
        writer.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.writexml(writer, '', '    ', '\n')
        return writer.getvalue()

    def save(self, filename):
        """
        Save Node to file
        """
        open(filename, 'w').write(self.toxml())


def create(filename=None, root=''):
    """
    Load or create an XML document.

    @returns Node object
    """
    if filename:
        doc = xml.dom.minidom.parse(filename)
        doc.dirname = os.path.dirname(filename)
        tree = doc.firstChild
        if root and tree.nodeName != root:
            raise RuntimeError('%s has wrong root node' % filename)
        return Node(tree)
    if not root:
        raise RuntimeError('no root node given')
    doc = xml.dom.minidom.Document()
    doc.dirname = ''
    tree = doc.createElement(root)
    doc.appendChild(tree)
    return Node(tree)
