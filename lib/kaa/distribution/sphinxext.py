# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# sphinxext.py - Kaa specific extensions for Sphinx
# -----------------------------------------------------------------------------
# $Id: sphinxext.py 4070 2009-05-25 15:32:31Z tack $
# -----------------------------------------------------------------------------
# Copyright 2009 Dirk Meyer, Jason Tackaberry
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
Defines the following new directives:

   .. kaaclass:: kaa.SomeClassName
   
     Top-most directive for all other custom kaa directives.  There are no
     options.

     A synopsis is automatically included, which provides (in this order)

        - The class hierarchy
        - Any class attributes explicitly provided via the classattrs
          directive.
        - Methods via the automethod directive
        - Properties via the autoproperties directive
        - Signals via the autosignals directive


    Any of following directives can be nested inside a kaaclass directive.
    Arguments following the directive are ignored (the class name is gotten
    from the outside kaaclass directive):

     .. classattrs::

        .. attribute:: SOME_CONSTANT

           Description of class variable SOME_CONSTANT.

        .. attribute:: [...]

           Any number of attribute directives may be nested under a classattrs
           directive.  They will all be included in the Class Attributes
           synopsis table in the order specified here.


     .. automethods::

        Automatically insert all methods defined in the class specified in the
        outer kaaclass directive.  Additional methods may be defined like so:

        .. method:: additional_method(arg1, arg2)

           A brief, one-line description of additional_method()

           :param arg1: don't forget to document any arguments.


        Takes the following options:

           :inherit:

              Includes all members from parent classes.

           :add: meth1[, meth2[, meth3[, ...]]]

              Includes the methods specified from parent classes.
           
           :remove: meth1[, meth2[, meth3[, ...]]]

              Prevents the specified methods from appearing where they would
              normally be auto-included.

           :order: meth1[, meth2[, meth3[, ...]]]

              Overrides the order for which the methods are listed.  Not all
              methods need to be specified here: methods that are specified
              will be listed first and in the given order.  All other methods
              will follow in the canonical order.

    
     .. autoproperties::

        Automatically insert all properties defined in the class specified in the
        outer kaaclass directive.  Additional properties (or attributes that
        aren't necessarily implemented as properties) may be defined like so:

        .. attribute:: some_other_prop

           A brief, one-line description of some_other_prop.

           More detailed description if desired.

        Options are the same as the automethods directive.
        

     .. autosignals::

        Automatically insert all signals defined in the class specified in the
        outer kaaclass directive.  Additional signals maybe defined like so:

        .. attribute:: signals.some_other_signal

           A brief, one-line description of some_other_signal.

           .. describe:: def callback(arg1, arg2, ...)

              :param arg1: don't forget to document callback arguments.
           
           A more detailed description of signal, if desired.

           Note that the signals name following the attribute directive is
           prefixed with 'signals.'  This is important.  The 'signals.' part
           is stripped for display purposes.

        Options are the same as the automethods directive.
      


Example usage:

.. kaaclass:: kaa.SomeClass

   .. classattrs::

      .. attribute:: SOME_CONST

         Definition of SOME_COST.

         Can of course contain :attr:`references`.
      
      .. attribute:: some_other_class_variable

    .. automethods::
       :add: superclass_method_foo
       :remove: deprecated_method
       :order: superclass_method_foo, read, write, custom_method, close

       .. method:: custom_method(arg1, arg2)

          Short description of custom_method.

          :param arg1: and of course the argument descriptions.
          :param arg2: same here.

          Additional info about custom_method which won't show up in the
          synopsis table.

    .. autoproperties::
       :inherit:
       :remove: stupid_super_class_method

    .. autosignals::
"""


# Python imports
import re

# Sphinx imports
from sphinx.util.compat import make_admonition
from sphinx.ext.autodoc import prepare_docstring
import sphinx.addnodes

# Docutils imports
from docutils.parsers.rst import directives
from docutils import nodes
from docutils.statemachine import ViewList, StringList
from docutils.parsers.rst import directives

# Kaa imports
from kaa.object import get_all_signals


# Custom nodes
class synopsis(nodes.paragraph):
    @staticmethod
    def visit(document, node):
        document.body.append('<div class="heading">%s</div>' % node['title'])
        if node['title'] != 'Class Hierarchy':
            document.body.append('\n<table>\n')

    @staticmethod
    def depart(document, node):
        if node['title'] != 'Class Hierarchy':
            document.body.append('</table>\n')


class hierarchy_row(nodes.paragraph):
    @staticmethod
    def visit(document, node):
        prefix = '%s%s' % ('&nbsp;' * 5 * (node.level-1), ('', '&#9492;&#9472; ')[node.level != 0])
        document.body.append(prefix)
        if node.level == node.depth:
            document.body.append('<tt class="xref docutils literal current">')


    @staticmethod
    def depart(document, node):
        if node.level == node.depth:
            document.body.append('</tt>')
        document.body.append('<br />')
    

class td(nodes.paragraph):
    @staticmethod
    def visit(document, node):
        if node.attributes.get('heading'):
            document.body.append('<th>')
        else:
            document.body.append(document.starttag(node, 'td', ''))

    @staticmethod
    def depart(document, node):
        if node.attributes.get('heading'):
            document.body.append('</th>')
        else:
            document.body.append('</td>')


class subsection(nodes.paragraph):
    @staticmethod
    def visit(document, node):
        document.body.append('<h4>%s</h4>' % node['title'])
        if node['title'] == 'Synopsis':
            document.body.append('<div class="kaa synopsis">\n')

    @staticmethod
    def depart(document, node):
        if node['title'] == 'Synopsis':
            document.body.append('\n</div>\n')


def get_signals(cls, inherit, add, remove):
    if inherit:
        signals = get_all_signals(cls)
    else:
        signals = getattr(cls, '__kaasignals__', {}).copy()
        if add:
            all = get_all_signals(cls)
            for key in add:
                signals[key] = all[key]

    for key in remove:
        del signals[key]

    for key, val in signals.items():
        yield key, val


def get_members(cls, inherit, add, remove, pre_filter, post_filter):
    if inherit:
        keys = dir(cls)
    else:
        keys = cls.__dict__.keys()

    keys = set([ name for name in keys if pre_filter(name, getattr(cls, name)) ])
    keys.update(set(add))
    keys = keys.difference(set(remove))
    keys = [ name for name in keys if post_filter(name, getattr(cls, name)) ]
    
    for name in sorted(keys):
        yield name, getattr(cls, name)


def get_methods(cls, inherit=False, add=[], remove=[]):
    return get_members(cls, inherit, add, remove,
                       lambda name, attr: not name.startswith('_'),
                       lambda name, attr: callable(attr))


def get_properties(cls, inherit=False, add=[], remove=[]):
    return get_members(cls, inherit, add, remove,
                       lambda name, attr: not name.startswith('_'),
                       lambda name, attr: isinstance(attr, property))


def get_class(fullname):
    mod, clsname = fullname.rsplit('.', 1)
    cls = getattr(__import__(mod, None, None, ['']), clsname)
    return cls


def normalize_class_name(mod, name):
    for i in reversed(range(mod.count('.')+1)):
        fullname = '%s.%s' % (mod.rsplit('.', i)[0], name)
        try:
            get_class(fullname)
            return fullname
        except (ImportError, AttributeError):
            pass
    return '%s.%s' % (mod, name)
    

def append_class_hierarchy(node, state, cls, level=0, clstree=None):
    if clstree is None:
        clstree = []

    name = normalize_class_name(cls.__module__, cls.__name__)
    clstree.append((level, name))

    for c in cls.__bases__:
        if c != object:
            append_class_hierarchy(node, state, c, level+1, clstree)

    if level == 0:
        clstree = sorted(set(clstree), key=lambda x: -x[0])
        depth = max(clstree, key=lambda x: x[0])[0]
        for level, name in [ (abs(level-depth), cls) for level, cls in clstree ]:
            row = hierarchy_row()
            row.level, row.depth = level, depth

            if level != depth:
                name = ':class:`%s`' % name

            list = ViewList()
            list.append(name, '')
            state.nested_parse(list, 0, row)
            node.append(row)



def auto_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    inherit = 'inherit' in options
    add = options.get('add', [])
    remove = options.get('remove', [])

    cls = env._kaa_current_class
    clsname = env._kaa_current_class_name
    env._kaa_class_info.append(name)
    list = ViewList()
    section = subsection()
    section['title'] = name[4:].title()

    if name == 'automethods':
        for attrname, method in get_methods(cls, inherit, add, remove):
            list.append(u'.. automethod:: %s.%s' % (clsname, attrname), '')
    elif name == 'autoproperties':
        for attrname, prop in get_properties(cls, inherit, add, remove):
            list.append(u'.. autoattribute:: %s.%s' % (clsname, attrname), '')
    elif name == 'autosignals':
        for attrname, docstr in get_signals(cls, inherit, add, remove):
            list.append(u'.. attribute:: signals.%s' %  attrname, '')
            list.append(u'', '')
            for line in docstr.split('\n'):
                list.append(line, '')
            list.append(u'', '')

    if not len(list) and not content:
        return []

    state.nested_parse(list, 0, section)
    state.nested_parse(content, 0, section) 

    if name == 'autosignals':
        # We're using signals.foo for signals attribute names.  We don't
        # want to output 'signals.' for the displayable signal name, so
        # we need to strip that out.
        for child in section.children:
            if not isinstance(child, sphinx.addnodes.desc) or not child.children:
                continue

            # Change displayed signal name from signals.foo to foo.
            desc_sig = child.children[0]
            name_prefix = str(desc_sig[0].children[0])
            if name_prefix != 'signals.':
                # Signal names can have dashes (-) but if they do, sphinx
                # considers this an invalid attribute name (because we're
                # using '.. attribute') and so generates
                #    <desc_name>signals.foo-bar</descname> 
                # and the desc_signature has no ids attribute, which we
                # need to set to make it linkable.
                desc_sig[0].children[0] = nodes.Text(name_prefix[8:])
                new_id = u'%s.%s' % (clsname, name_prefix)
                desc_sig['ids'] = [new_id]
                # Add this signal to Sphinx's descref dict so references
                # to this signal are properly resolved.
                env.descrefs[new_id] = (env.docname, 'attribute')

            else:
                # Removes <descaddname>signals.</descaddname>
                desc_sig.remove(desc_sig[0])

    if 'order' in options:
        def keyfunc(member):
            try:
                return options['order'].index(member[0])
            except ValueError:
                return 100000

        sorted = section.copy()
        members = []  # (name, [child1, child2, ...])
        for node in section.children:
            if isinstance(node, sphinx.addnodes.index):
                name = node['entries'][0][1].split()[0].rstrip('()')
                members.append((name, []))
            members[-1][1].append(node)

        members.sort(key=keyfunc)
        for name, children in members:
            sorted.extend(children)
        section = sorted

    return [section]


def members_option(arg):
    if arg is None:
        return ['__all__']
    return [ x.strip() for x in arg.split(',') ]


def classattrs_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    section = subsection()
    section['title'] = 'Class Attributes'
    state.nested_parse(content, 0, section)
    return [section]


def kaaclass_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    env._kaa_class_info = []
    list = ViewList()
    list.append('.. autoclass:: %s' % arguments[0], '')
    list.append('', '')
    list.append('   .. autosynopsis:: %s' % arguments[0], '')
    list.append('', '')
    for line in content:
        list.append('      ' + line, '')

    para = nodes.paragraph()
    state.nested_parse(list, 0, para)
    return [para]


def synopsis_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    env = state.document.settings.env
    cls = get_class(arguments[0])
    env._kaa_current_class = cls
    env._kaa_current_class_name = clsname = arguments[0]
    env.currmodule, env.currclass = clsname.rsplit('.', 1)

    para = nodes.paragraph()

    section_synopsis = subsection(title='Synopsis')
    para.append(section_synopsis)

    state.nested_parse(content, 0, para)

    syn = synopsis(title='Class Hierarchy')
    syn_para = nodes.paragraph(classes=['hierarchy'])
    section_synopsis.append(syn)
    append_class_hierarchy(syn_para, state, cls)
    syn.append(syn_para)

    ci = env._kaa_class_info
    append_synopsis_section(state, section_synopsis, para, 'Class Attributes', 'attr', 'classattrs' not in ci)
    append_synopsis_section(state, section_synopsis, para, 'Methods', 'meth', 'automethods' not in ci)
    append_synopsis_section(state, section_synopsis, para, 'Properties', 'attr', 'autoproperties' not in ci)
    append_synopsis_section(state, section_synopsis, para, 'Signals', 'attr', 'autosignals' not in ci)
    return [para]


def find_subsection_node(search_node, title):
    for node in search_node.traverse(subsection):
        if node['title'] == title:
            return node


def append_synopsis_section(state, section_synopsis, search_node, title, role, optional=False):
    env = state.document.settings.env
    clsname = env._kaa_current_class_name
    cls = env._kaa_current_class
    # Crawl through the nodes for section titled the given title ('Methods',
    # 'Properties', etc) and look for all the <desc> nodes, which contain
    # methods or attributes.  Construct a list called members whose first
    # element contains the name of the member, and whose last element contains
    # the first paragraph node of the description.
    members = []
    subsection_node = find_subsection_node(search_node, title)
    if subsection_node and subsection_node.children:
        desc_nodes = subsection_node.children[0].traverse(sphinx.addnodes.desc, descend=0, siblings=1)
    else:
        desc_nodes = []

    for node in desc_nodes:
        sig = node.first_child_matching_class(sphinx.addnodes.desc_signature)
        content = node.first_child_matching_class(sphinx.addnodes.desc_content)
        pidx = node.children[content].first_child_matching_class(nodes.paragraph)
        name = node.children[sig]['ids'][0].split('.')[-1]

        desc = nodes.Text('')
        if pidx is not None:
            desc = node.children[content].children[pidx].deepcopy()
        
        if subsection_node['title'] == 'Properties':
            prop = getattr(cls, name.split('.')[-1], None)
            perm = 'unknown'
            if prop:
                if prop.fset and not prop.fget:
                    perm = 'write-only'
                elif prop.fget and not prop.fset:
                    perm = 'read-only'
                else:
                    perm = 'read/write'
            members.append((name, nodes.Text(perm), desc))
        else:
            members.append((name, desc))

    # If no members found and this section is optional (Class Attributes),
    # we're done.
    if not members and optional:
        return

    # Create a new synopsis section with the given title.
    syn = synopsis(title=title)
    section_synopsis.append(syn)
    if not members:
        # Mandatory section and no members, so we say so.
        syn.append(nodes.paragraph('', 'This class has no %s.' % title.lower()))

    # Loop through all members and add rows to the synopsis section table.
    for info in members:
        row = nodes.row()
        syn.append(row)

        # First columns is a <th> with the member name, cross referenced
        # to the actual member on this page.
        name = info[0]
        col = td(heading=True)
        row.append(col)
        list = ViewList()
        if title == 'Signals':
            name = 'signals.' + name
        list.append(':%s:`~%s`' % (role, clsname + '.' + name), '')
        state.nested_parse(list, 0, col)

        # Add remaining columns from member info.
        for col_info in info[1:]:
            col = td()
            col.append(col_info)
            row.append(col)

        # Last column has 'desc' class (disables nowrap).
        col['classes'] = ['desc']


def setup(app):
    auto_options = {
        'inherit': directives.flag,
        'add': members_option,
        'remove': members_option,
        'order': members_option,
    }

    app.add_node(subsection, html=(subsection.visit, subsection.depart))
    app.add_node(synopsis, html=(synopsis.visit, synopsis.depart))
    app.add_node(td, html=(td.visit, td.depart))
    app.add_node(hierarchy_row, html=(hierarchy_row.visit, hierarchy_row.depart))
    app.add_directive('kaaclass', kaaclass_directive, 1, (0, 1, 1))
    app.add_directive('autosynopsis', synopsis_directive, 1, (0, 1, 1))
    app.add_directive('autoproperties', auto_directive, 1, (0, 1, 1), **auto_options)
    app.add_directive('automethods', auto_directive, 1, (0, 1, 1), **auto_options)
    app.add_directive('autosignals', auto_directive, 1, (0, 1, 1), **auto_options)
    app.add_directive('classattrs', classattrs_directive, 1, (0, 1, 0))
