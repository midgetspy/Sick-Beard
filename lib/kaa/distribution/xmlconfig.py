# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# xmlconfig.py - xml config to python converter
# -----------------------------------------------------------------------------
# $Id: xmlconfig.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'convert' ]

# python imports
import pprint

# use minidom because it is part of the python distribution.
# pyxml replaces the parser but everything used here should
# work even without it.
from xml.dom import minidom

def get_value(value, type):
    if not value:
        return eval('%s()' % type)
    if type:
        return eval(type)(value)
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    if value.isdigit():
        return int(value)
    return str(value)


def format_content(node):
    s = node.childNodes[0].data.replace('\t', '        ')
    spaces = ''
    while s:
        if s[0] == ' ':
            spaces += ' '
            s = s[1:]
            continue
        if s[0] == '\n':
            spaces = ''
            s = s[1:]
            continue
        break
    return s.replace('\n' + spaces, '\n').strip()


def nodefilter(node, *names):
    return [ n for n in node.childNodes if n.nodeName in names ]


class Parser(object):

    def __init__(self, package):
        self._package = package

    def _get_schema(self, node):
        schema = []
        for child in node.childNodes:
            if hasattr(self, '_parse_%s' % child.nodeName):
                schema.append(child)
        return schema


    def parse(self, node, fd, deep=''):
        fd.write('%s(' % node.nodeName.capitalize())
        first = True
        if node.getAttribute('name'):
            fd.write('name=\'%s\'' % node.getAttribute('name'))
            first = False
        for child in nodefilter(node, 'desc'):
            if not first:
                fd.write(', ')
            first = False
            desc = format_content(child).replace('\'', '\\\'')
            if desc.find('\n') > 0:
                desc = deep + desc.replace('\n', '\n' + deep)
                fd.write('desc=\'\'\'\n%s\n%s\'\'\'' % (desc, deep))
            else:
                fd.write('desc=\'%s\'' % desc)
        getattr(self, '_parse_%s' % node.nodeName.lower())(node, fd, deep, first)


    def _parse_var(self, node, fd, deep, first):
        default = node.getAttribute('default')
        deftype = node.getAttribute('type')
        if default or deftype:
            if not first:
                fd.write(', ')
            first = False
            default = get_value(default, deftype)
            fd.write('default=%s' % pprint.pformat(default).strip())

        for child in nodefilter(node, 'values'):
            if not first:
                fd.write(', ')
            first = False
            values = []
            for value in nodefilter(child, 'value'):
                content = value.childNodes[0].data
                values.append(get_value(content, value.getAttribute('type')))
            fd.write('type=%s' % pprint.pformat(tuple(values)).strip())
            break
        fd.write(')')


    def _parse_config(self, node, fd, deep, first):
        self._parse_group(node, fd, deep, first)


    def _parse_group(self, node, fd, deep, first):
        if not first:
            fd.write(', ')
        deep = deep + '  '
        fd.write('schema=[\n\n' + deep)
        for s in self._get_schema(node):
            self.parse(s, fd, deep)
            fd.write(',\n\n' + deep)
        deep = deep[:-2]
        fd.write(']\n' + deep)
        if node.nodeName == 'config':
            fd.write(", module='%s.config'" % self._package)
        fd.write(')')


    def _parse_list(self, node, fd, deep, first):
        if not first:
            fd.write(', ')
        schema = self._get_schema(node)
        fd.write('schema=')
        if len(schema) > 1:
            deep = deep + '  '
            fd.write('[\n\n' + deep)
        for s in schema:
            self.parse(s, fd, deep)
            if len(schema) > 1:
                fd.write(',\n\n' + deep)
        if len(schema) > 1:
            deep = deep[:-2]
            fd.write(']\n' + deep)
        type = node.getAttribute('type')
        if type and node.nodeName == 'dict':
            fd.write(', type=%s' % type)
        defaults = {}
        for var in nodefilter(node, 'set'):
            value = get_value(var.getAttribute('value'), None)
            defaults[var.getAttribute('key')] = value
        if defaults:
            fd.write(', defaults=%s' % pprint.pformat(defaults).strip())

        fd.write(')')


    def _parse_dict(self, node, fd, deep, first):
        self._parse_list(node, fd, deep, first)



def convert(xml, python, package):
    tree = minidom.parse(xml).firstChild
    if tree.nodeName != 'config':
        raise RuntimeError('%s is no valid cxml file' % xml)

    # out = sys.__stdout__
    out = open(python, 'w')

    out.write('# auto generated file\n\n')
    out.write('from kaa.config import Var, Group, Dict, List, Config\n\n')
    out.write('config = ')

    Parser(package).parse(tree, out)
    out.write('\n\n')
    for child in tree.childNodes:
        if child.nodeName != 'code':
            continue
        out.write(format_content(child) + '\n\n')
