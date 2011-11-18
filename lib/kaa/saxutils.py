# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# saxutils.py - some classes helping dealing with xml files
# -----------------------------------------------------------------------------
# $Id: saxutils.py 4070 2009-05-25 15:32:31Z tack $
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

__all__ = [ 'Element', 'ElementParser', 'pprint' ]

# python imports
import os
import codecs
import xml.sax
import xml.sax.saxutils

# we can't use cStringIO since it doesn't support Unicode strings
from StringIO import StringIO

# unicode helper functions
from strutils import unicode_to_str, str_to_unicode

class Element(object):
    """
    Simple XML element that can have either a text content or child
    elements. This is common for config files, Freevo fxd files, XMPP
    stanzas, and many other use cases. It is possible to access the
    attribute or the (first) child by accessing a member variable with
    that name. If the name exists as attribute and child or if there
    are several children by that name, additional helper functions are
    provided. The element's name can be accessed using the tagname
    member variable.

    A special variable is 'content'. If provided to __init__, it can
    contain text element's children (either a list of Elements or one
    Element) or the text of the element. The same is true when
    accessing Element.content. If the element has children, the
    attribute or child with that name is returned (or None if it does
    not exist). If it is a node without children, Element.content will
    refer to the text content.

    SAX parser have to use the internal variables _children, _attr,
    and _content.
    """
    def __init__(self, tagname, xmlns=None, content=None, **attr):
        self.tagname = tagname
        self.xmlns = xmlns
        self._content = ''
        self._children = []
        self._attr = attr
        if content:
            if isinstance(content, (list, tuple)):
                self._children = content
            elif isinstance(content, Element):
                self._children = [ content ]
            else:
                self._content = content

    def append(self, element):
        """
        Append an element to the list of children.
        """
        self._children.append(element)

    def add_child(self, tagname, xmlns=None, content=None, **attr):
        """
        Append an element to the list of children.
        """
        element = Element(tagname, xmlns, content, **attr)
        self._children.append(element)
        return element

    def has_child(self, name):
        """
        Return if the element has at least one child with the given element name.
        """
        return self.get_child(name) is not None

    def get_child(self, name):
        """
        Return the first child with the given name or None.
        """
        for child in self._children:
            if child.tagname == name:
                return child
        return None

    def get_children(self, name=None):
        """
        Return a list of children with the given name.
        """
        if name is None:
            return self._children[:]
        children = []
        for child in self._children:
            if child.tagname == name:
                children.append(child)
        return children

    def __iter__(self):
        """
        Iterate through the children.
        """
        return self._children.__iter__()

    def get(self, item, default=None):
        """
        Get the given attribute value or None if not set.
        """
        return self._attr.get(item, default)

    def __getitem__(self, item):
        """
        Get the given attribute value or raise a KeyError if not set.
        """
        return self._attr[item]

    def __setitem__(self, item, value):
        """
        Set the given attribute to a new value.
        """
        self._attr[item] = value

    def __getattr__(self, attr):
        """
        Magic function to return the attribute or child with the given name.
        """
        if attr == 'content' and not self._children:
            return self._content
        result = self._attr.get(attr)
        if result is not None:
            return result
        result = self.get_child(attr)
        if result is not None:
            return result
        if '_' in attr:
            return getattr(self, attr.replace('_', '-'))

    def __cmp__(self, other):
        if isinstance(other, (str, unicode)):
            return cmp(self.tagname, other)
        return object.__cmp__(self, other)

    def __repr__(self):
        """
        Python representation string
        """
        return '<Element %s>' % self.tagname

    def __unicode__(self):
        """
        Convert the element into an XML unicode string.
        """
        result = u'<%s' % self.tagname
        if self.xmlns:
            result += u' xmlns="%s"' % self.xmlns
        for key, value in self._attr.items():
            if value is None:
                continue
            if isinstance(value, str):
                value = str_to_unicode(value)
            if not isinstance(value, unicode):
                value = unicode(value)
            result += u' %s=%s' % (key, xml.sax.saxutils.quoteattr(value))
        if not self._children and not self._content:
            return result + u'/>'
        result += u'>'
        for child in self._children:
            if not isinstance(child, Element):
                child = child.__xml__()
            result += unicode(child)
        return result + xml.sax.saxutils.escape(self._content.strip()) + u'</%s>' % self.tagname

    def __str__(self):
        """
        Convert the element into an XML string using the current
        string encoding.
        """
        return unicode_to_str(unicode(self))


class ElementParser(xml.sax.ContentHandler):
    """
    Handler for the SAX parser. The member function 'handle' will be
    called everytime an element given on init is closed. The parameter
    is the tree with this element as root. An element can either have
    children or text content. The ElementParser is usefull for simple
    xml files found in config files and information like epg data.
    """
    def __init__(self, *names):
        """
        Create handler with a list of element names.
        """
        self._names = names
        self._elements = []
        self.attr = {}
        
    def startElement(self, name, attr):
        """
        SAX callback
        """
        element = Element(name)
        element._attr = dict(attr)
        if len(self._elements):
            self._elements[-1].append(element)
        else:
            self.attr = dict(attr)
        self._elements.append(element)

    def endElement(self, name):
        """
        SAX callback
        """
        element = self._elements.pop()
        element._content = element._content.strip()
        if name in self._names or (not self._names and len(self._elements) == 1):
            self.handle(element)
        if not self._elements:
            self.finalize()

    def characters(self, c):
        """
        SAX callback
        """
        if len(self._elements):
            self._elements[-1]._content += c

    def handle(self, element):
        """
        ElementParser callback for a complete element.
        """
        pass

    def finalize(self):
        """
        ElementParser callback at the end of parsing.
        """
        pass


def pprint(element):
    """
    Convert Element object into an UTF-8 string with indention
    """
    def convert(write, element, indent=u'', addindent=u'', newl=u''):
        """
        Write the element and all children
        """
        write(indent+"<" + element.tagname)
        # write attributes
        for key, value in element._attr.items():
            write(" %s=" % key)
            write(xml.sax.saxutils.quoteattr(value))
        if element._content:
            # write text content
            write(">")
            write(xml.sax.saxutils.escape(element._content))
            write("</%s>%s" % (element.tagname, newl))
        elif element._children:
            # write children
            write(">%s" % newl)
            for child in element:
                if not isinstance(child, Element):
                    child = child.__xml__()
                convert(write, child, indent+addindent, addindent, newl)
            write("%s</%s>%s" % (indent, element.tagname, newl))
        else:
            # no children
            write("/>%s" % newl)

    writer = codecs.lookup('utf8')[3](StringIO())
    writer.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    convert(writer.write, element, '', '    ', '\n')
    return writer.getvalue()
