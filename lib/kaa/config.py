# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# config.py - config file reader
# -----------------------------------------------------------------------------
# $Id: config.py 4077 2009-05-25 18:21:02Z tack $
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

__all__ = [ 'Var', 'Group', 'Dict', 'List', 'Config', 'set_default',
            'get_description', 'get_config' ]

# Python imports
import os
import re
import copy
import logging
import stat
import md5
import textwrap
from new import classobj

# kaa.base modules
from strutils import str_to_unicode, unicode_to_str, get_encoding
from callback import Callback, WeakCallback
from timer import WeakTimer, WeakOneShotTimer
from kaa.inotify import INotify
from utils import property
import main

# get logging object
log = logging.getLogger('config')

# align regexp
align = re.compile(u'\n( *)[^\n]', re.MULTILINE)

def _format(text):
    """
    Format a description with multiple lines.
    """
    if text.find('\n') == -1:
        return text.strip()

    # This can happen if you use multiple lines and use the python
    # code formating. So there are spaces at each line. Find the maximum
    # number of spaces to delete.

    # description with more than one line, format the text
    if not text.startswith(u'\n'):
        # add newline at the beginning for regexp
        text = u'\n' + text
    # align desc
    strip = 100
    for m in align.findall(text, re.MULTILINE):
        strip = min(len(m), strip)
    if strip == 100 or strip < 1:
        # nothing found
        return text

    newtext = []
    for line in text.split(u'\n'):
        newtext.append(line[strip+1:])
    return u'\n'.join(newtext)[1:].strip()


class Base(object):
    """
    Base class for all config objects.
    """

    def __init__(self, name='', desc=u'', default=None):
        super(Base, self).__init__()
        self._parent = None
        self._name = name
        self._desc = _format(str_to_unicode(desc))
        self._default = default
        self._value = default
        self._monitors = []


    def _hash(self, values=True):
        """
        Returns a hash of the config item.

        If values is False, don't include the value in the hash, effectively taking
        a hash of the schema only.
        """
        value = repr(self._value) if values else ''
        return md5.new(repr(self._name) + repr(self._desc) + repr(self._default) + value).hexdigest()


    def copy(self):
        """
        Return a deep copy of the object.
        """
        return copy.deepcopy(self)

    def add_monitor(self, callback):
        # Wrap the function or method in a class that will ignore deep copies
        # because deepcopy() is unable to copy callables.
        self._monitors.append(Callback(callback))

    def remove_monitor(self, callback):
        for monitor in self._monitors:
            if callback == monitor:
                self._monitors.remove(monitor)

    def _notify_monitors(self, oldval):
        names = []
        o = self
        while o:
            if o._name:
                if names and names[0][0] == "[":
                    # List/dict index, just concat to previous name.
                    names[0] = o._name + names[0]
                else:
                    names.insert(0, o._name)

            for monitor in o._monitors:
                if not callable(monitor):
                    # Happens when deepcopying, callables don't get copied,
                    # they become None.  So remove them now.
                    o._monitors.remove(monitor)
                if names:
                    name = ".".join(names)
                else:
                    name = None
                monitor(name, oldval, self._value)
            o = o._parent


    @property
    def parent(self):
        return self._parent


    def __repr__(self):
        return repr(self._value)


class VarProxy(Base):
    """
    Wraps a config variable value, inheriting the actual type of that
    value (int, str, unicode, etc.) and offers add_monitor and remove_monitor
    methods to manage the monitor list of the original Var object.
    """
    def __new__(cls, item):
        clstype = realclass = type(item._value)
        if clstype == bool:
            # You can't subclass a boolean, so use int instead.  In practice,
            # this isn't a problem, since __class__ will end up being bool,
            # thanks to __getattribute__, so isinstance(o, bool) will be True.
            clstype = int

        newclass = classobj("VarProxy", (clstype, cls), {
            "__getattribute__": cls.__getattribute__,
            "__str__": cls.__str__,
        })

        if item._value:
            self = newclass(item._value)
        else:
            self = newclass()

        self._class = realclass
        return self


    def __init__(self, value = None):
        if not isinstance(value, Var):
            # Called inside __new__ when we pass the intrinsic value for this
            # config variable
            super(VarProxy, self).__init__(default = value)
        else:
            # Called implicitly after returning from __new__, here value will
            # be a kaa.config.Var
            self._monitors = value._monitors
            self._parent = value._parent
            self._item = value


    def __getattribute__(self, attr):
        if attr == "__class__":
            return super(VarProxy, self).__getattribute__("_class")
        return super(VarProxy, self).__getattribute__(attr)

    def __str__(self):
        return self._class.__str__(self)

    def __repr__(self):
        return self._class.__repr__(self)


class Var(Base):
    """
    A config variable.
    """
    def __init__(self, name='', type='', desc=u'', default=None):
        super(Var, self).__init__(name, desc, default)
        if type == '':
            # create type based on default
            if default == None:
                raise AttributeError('define type or default')
            type = default.__class__

        self._type = type


    def _hash(self, values=True):
        """
        Returns a hash of the config item.
        """
        return md5.new(super(Var, self)._hash(values) + repr(self._type)).hexdigest()


    def _cfg_string(self, prefix, print_desc=True):
        """
        Convert object into a string to write into a config file.
        """
        # create description
        desc = comment = ''
        if print_desc:
            if self._desc:
                desc = '# | %s\n' % unicode_to_str(self._desc).replace('\n', '\n# | ')
                if isinstance(self._type, (tuple, list)):
                    # Show list of allowed values for this tuple variable.
                    if type(self._type[0]) == type(self._type[-1]) == int and \
                       self._type == range(self._type[0], self._type[-1]):
                        # Type is a range
                        allowed = '%d-%d' % (self._type[0], self._type[-1])
                    else:
                        allowed = ', '.join([ str(x) for x in self._type ])
                    allowed = textwrap.wrap(allowed, 78,
                                          initial_indent = '# | Allowed values: ',
                                          subsequent_indent = '# |' + 17 * ' ')
                    desc += '\n'.join(allowed) + '\n'

                if self._value != self._default:
                    # User value is different than default, so include default
                    # in comments for reference.
                    desc += '# | Default: ' + str(self._default) + '\n'

        if self._value == self._default:
            # Value is set to default, so comment it out in config file.
            comment = '# '

        value = unicode_to_str(self._value)
        prefix += self._name
        return '%s%s%s = %s' % (desc, comment, prefix, value)


    def _cfg_set(self, value, default=False):
        """
        Set variable to value. If the type is not right, an expection will
        be raised. The function will convert between string and unicode.
        If default is set to True, the default value will also be changed.
        """
        if isinstance(self._type, (list, tuple)):
            if not value in self._type:
                # This could crash, but that is ok
                value = self._type[0].__class__(value)
            if not value in self._type:
                allowed = [ str(x) for x in self._type ]
                raise AttributeError('Variable must be one of %s' % ', '.join(allowed))
        elif not isinstance(value, self._type):
            if self._type == str:
                value = unicode_to_str(value)
            elif self._type == unicode:
                value = str_to_unicode(value)
            elif self._type == bool:
                if not value or value.lower() in ('0', 'false', 'no'):
                    value = False
                else:
                    value = True
            else:
                # This could crash, but that is ok
                value = self._type(value)
        if default:
            self._default = value
        if self._value != value:
            oldval = self._value
            self._value = value
            self._notify_monitors(oldval)
        return value


class Group(Base):
    """
    A config group.
    """
    def __init__(self, schema, desc=u'', name='', desc_type='default'):
        super(Group, self).__init__(name, desc)
        self._dict = {}
        self._vars = []
        self._schema = schema
        # 'default' will print all data
        # 'group' will only print the group description
        self._desc_type = desc_type

        for data in schema:
            if not data._name:
                raise AttributeError('no name given')
            if data._name in self.__class__.__dict__:
                raise ValueError('Config name "%s" conflicts with internal method or property' % data._name)
            self._dict[data._name] = data
            self._vars.append(data._name)

        # the value of a group is the group itself
        self._value = self

        # Parent all the items in the schema
        for item in schema:
            item._parent = self


    def add_variable(self, name, value):
        """
        Add a variable to the group. The name will be set into the
        given value. The object will _not_ be copied.
        """
        if name in self.__class__.__dict__:
            raise ValueError('Config name "%s" conflicts with internal method or property' % name)
        value._name = name
        value._parent = self
        self._dict[name] = value
        self._vars.append(name)


    @property
    def variables(self):
        """
        List of variables for this group.
        """
        return self._vars


    def _hash(self, values=True):
        """
        Returns a hash of the config item.
        """
        hash = md5.new(super(Group, self)._hash(values))
        for name in self._vars:
            hash.update(self._dict[name]._hash(values))
        return hash.hexdigest()


    def _cfg_string(self, prefix, print_desc=True):
        """
        Convert object into a string to write into a config file.
        """
        ret  = []
        desc = unicode_to_str(self._desc.strip('\n')).replace('\n', '\n# | ')
        is_anonymous = self._name.endswith(']')

        if print_desc and self._name and not is_anonymous:
            sections = [ x.capitalize() for x in prefix.rstrip('.').split('.') + [self._name] ]
            breadcrumb = ' > '.join(filter(len, sections))
            ret.append('#\n# Begin Group: %s\n#' % breadcrumb)

        if self._name:
            prefix = '%s%s.' % (prefix, self._name)
        print_var_desc = print_desc

        if prefix and desc and not is_anonymous and print_desc:
            ret.append('# | %s\n#' % desc)
            if self._desc_type != 'default':
                print_var_desc = False

        # Iterate over group vars and fetch their cfg strings, also
        # deterining if we need to space them (by separating with a
        # blank commented line), which we do if
        var_strings = []
        space_vars = False
        n_nongroup = 0
        for name in self._vars:
            var = self._dict[name]
            var_is_group = isinstance(var, (Group, Dict))
            cfgstr = var._cfg_string(prefix, print_var_desc)
            if not var_is_group:
                n_nongroup += 1
                space_vars = space_vars or '\n' in cfgstr
            var_strings.append((cfgstr, var_is_group))

        for (cfgstr, var_is_group) in var_strings:
            if var_is_group and (not ret or not ret[-1].endswith('\n')):
                # Config item is a group or list, space it down with a blank
                # line for readability.
                ret.append('')
            ret.append(cfgstr)
            if not var_is_group and space_vars and n_nongroup > 1:
                # We need to space variables (see above), so add the empty
                # commented line.
                ret.append('#')

        if print_desc and self._name and not is_anonymous:
            if n_nongroup != len(self._vars) and (not ret or not ret[-1].endswith('\n')):
                # One of our variables is a group/dict, so add another
                # empty line to separate the stanza.
                ret.append('\n#')
            elif not space_vars or n_nongroup <= 1:
                ret.append('#')
            ret.append('# End Group: %s\n#\n' % breadcrumb)
        return '\n'.join(ret)


    def _cfg_get(self, key):
        """
        Get variable, subgroup, dict or list object (as object not value).
        """
        if not key in self._dict:
            if key.replace('_', '-') in self._dict:
                return self._dict[key.replace('_', '-')]
            return object.__getattribute__(self, key)
        return self._dict[key]


    def __setattr__(self, key, value):
        """
        Set a variable in the group.
        """
        if key.startswith('_') or key not in self._dict:
            return object.__setattr__(self, key, value)
        self._cfg_get(key)._cfg_set(value)


    def __getattr__(self, key):
        """
        Get variable, subgroup, dict or list.
        """
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        item = self._cfg_get(key)
        if isinstance(item, Var):
            return VarProxy(item)
        return item

    def __repr__(self):
        return repr(self._dict)


    def __iter__(self):
        return self._vars.__iter__()


class Dict(Base):
    """
    A config dict.
    """
    def __init__(self, schema, desc=u'', name='', type=unicode, defaults={}):
        super(Dict, self).__init__(name, desc)
        if isinstance(schema, (list, tuple)):
            schema = Group(schema=schema, desc=desc, name=name)
        self._schema = schema
        self._dict = {}
        self._type = type
        # the value of a dict is the dict itself
        self._value = self
        schema._parent = self
        for key, value in defaults.items():
            # FIXME: how to handle complex dict defaults with a dict in
            # dict or group in dict?
            var = self._cfg_get(key)
            var._default = var._value = value



    def keys(self):
        """
        Return the keys (sorted by name)
        """
        keys = self._dict.keys()[:]
        keys.sort()
        return keys


    def items(self):
        """
        Return key,value list (sorted by key name)
        """
        return [ (key, self._dict[key]._value) for key in self.keys() ]


    def values(self):
        """
        Return value list (sorted by key name)
        """
        return [ self._dict[key]._value for key in self.keys() ]


    def _hash(self, values=True):
        """
        Returns a hash of the config item.
        """
        hash = md5.new(super(Dict, self)._hash(values))
        for key in self.keys():
            hash.update(self._dict[key]._hash(values))
        return hash.hexdigest()


    def _cfg_string(self, prefix, print_desc=True):
        """
        Convert object into a string to write into a config file.
        """
        ret = []
        if print_desc:
            sections = [ x.capitalize() for x in prefix.rstrip('.').split('.') + [self._name] ]
            breadcrumb = ' > '.join(filter(len, sections))
            ret.append('#\n# Begin %s: %s\n#' % (self.__class__.__name__, breadcrumb))

        prefix = prefix + self._name

        if print_desc: #(type(self._schema) == Var and print_desc) or not self.keys():
            # TODO: more detailed comments, show full spec of var and some examples.
            ret.append('# | %s' % prefix)
            if self._desc:
                desc = unicode_to_str(self._desc).replace('\n', '\n# | ')
                ret.append('# |\n# | %s' % desc)

        var_strings = []
        space_vars = False
        for key in self.keys():
            cfgstr = self._dict[key]._cfg_string(prefix, False)
            var_strings.append(cfgstr)
            if '\n' in cfgstr:
                space_vars = True

        for cfgstr in var_strings:
            if '# Begin' in cfgstr and (not ret or not ret[-1].endswith('\n')):
                # Config item is a group or list, space it down with a blank
                # line for readability.
                ret.append('')
            ret.append(cfgstr)
            if space_vars:
                # Separate multi-line subgroups with newline.
                ret.append('')

        if print_desc:
            ret.append('#\n# End %s: %s\n#' % (self.__class__.__name__, breadcrumb))
        return '\n'.join(ret)


    def _cfg_get(self, index, create=True):
        """
        Get group or variable with the given index (as object, not value).
        """
        if not isinstance(index, self._type):
            if self._type == str:
                index = unicode_to_str(index)
            elif self._type == unicode:
                index = str_to_unicode(index)
            else:
                # this could crash, we don't care.
                index = self._type(index)
        if not index in self._dict and create:
            newitem = self._dict[index] = self._schema.copy()
            newitem._parent = self
            newitem._name = '[%s]' % unicode_to_str(index)
            if isinstance(newitem, Group):
                for item in newitem._schema:
                    item._parent = newitem
            elif isinstance(newitem, Dict):
                newitem._schema._parent = newitem

        return self._dict[index]


    def get(self, index):
        """
        Get group or variable with the given index. Return None if it does
        not exist.
        """
        try:
            return self._cfg_get(index, False)._value
        except KeyError:
            return None


    def __getitem__(self, index):
        """
        Get group or variable with the given index.
        """
        return self._cfg_get(index)._value


    def __setitem__(self, index, value):
        """
        Access group or variable with the given index.
        """
        self._cfg_get(index)._cfg_set(value)


    def __iter__(self):
        """
        Iterate through keys.
        """
        return self.keys().__iter__()


    def __nonzero__(self):
        """
        Return False if there are no elements in the dict.
        """
        return len(self._dict.keys()) > 0

    def __len__(self):
        """
        Returns number of items in the dict.
        """
        return len(self._dict.keys())


    def __repr__(self):
        return repr(self._dict)


class List(Dict):
    """
    A config list. A list is only a dict with integers as index.
    """
    def __init__(self, schema, desc=u'', name='', defaults=[]):
        defaults_dict = {}
        for key, value in enumerate(defaults):
            defaults_dict[key] = value
        super(List, self).__init__(schema, desc, name, int, defaults_dict)


    def __iter__(self):
        """
        Iterate through values.
        """
        return self.values().__iter__()

    def __repr__(self):
        return repr(self._dict.values())


class Config(Group):
    """
    A config object. This is a group with functions to load and save a file.
    """
    def __init__(self, schema, desc=u'', name='', module = None):
        super(Config, self).__init__(schema, desc, name)
        self._filename = None
        self._bad_lines = []
        self._loaded_hash_values = None   # hash for schema + values
        self._loaded_hash_schema = None   # hash for schema only
        self._module = module

        # Whether or not to autosave config file when options have changed
        self._autosave = None
        self._autosave_timer = WeakOneShotTimer(self.save)
        self.autosave = True

        # If we are watching the config file for changes.
        self._watching = False
        self._watch_mtime = 0
        self._watch_timer = WeakTimer(self._check_file_changed)
        self._inotify = None


    def _hash(self, values=True):
        """
        Returns a hash of the config item.
        """
        return md5.new(super(Config, self)._hash(values) + repr(self._bad_lines)).hexdigest()


    def copy(self):
        """
        Make a deepcopy of the config.  Reset the filename so we don't clobber
        the original config object's config file, and recreate the timers for
        the new object.
        """
        copy = Group.copy(self)
        copy._filename = None
        copy._watch_timer = WeakTimer(copy._check_file_changed)
        copy._autosave_timer = WeakOneShotTimer(copy.save)
        return copy


    def save(self, filename=None, force=False):
        """
        Save configuration file.

        :param filename: the name of the file to save; if None specified, will
                         use the name of the previously loaded file, or the
                         value assigned to the filename property.
        :param force: if False (default), will only write the file if there were
                      any changes (to either values or the schema).
        :type force: bool
        """
        if not filename:
            if not self._filename:
                raise ValueError, "Filename not specified and no default filename set."
            filename = self._filename

        # If this callback was added due to autosave, remove it now.
        main.signals['exit'].disconnect(self.save)

        hash_values = self._hash(values=True)
        if self._loaded_hash_values == hash_values and not force:
            # Nothing has changed, and forced save not required.
            return True

        filename = os.path.expanduser(filename)
        if os.path.dirname(filename) and not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        self._loaded_hash_schema = self._hash(values=False)
        self._loaded_hash_values = hash_values

        self._autosave_timer.stop()
        f = open(filename + '~', 'w')
        encoding = get_encoding().lower().replace('iso8859', 'iso-8859')
        f.write('# -*- coding: %s -*-\n' % encoding + \
                '# -*- hash: %s -*-\n' % self._loaded_hash_schema)
        if self._module:
            f.write('# -*- module: %s -*-\n' % self._module)
        f.write('# *************************************************************\n'
                '# WARNING: This file is auto-generated.  You are free to edit\n'
                '# this file to change config values, but any other changes\n'
                # FIXME: custom comments lost, would be nice if they were kept.  Might
                # be tricky to fix.
                '# (including removing or rearranging lines, or adding custom\n'
                '# comments) will be lost.\n'
                '#\n'
                '# The available settings are commented out with their default\n'
                '# values.\n'
                '# *************************************************************\n')
        if self._bad_lines:
            f.write('\n# =========================================================\n'
                    '# CAUTION: This file contains syntax errors or unsupported\n'
                    '# config settings, which were ignored.  Refer to the end of\n'
                    '# this file for the relevant lines.\n'
                    '# =========================================================\n')
        f.write(self._cfg_string('') + '\n')
        if self._bad_lines:
            f.write('\n\n\n'
                    '# *************************************************************\n'
                    '# The following lines caused errors and were ignored.  Possible\n'
                    '# reasons are removed variables or bad configuration.\n'
                    '# *************************************************************\n\n')
            for error, line in self._bad_lines:
                f.write('# %s\n%s\n\n' % (error, line))
        os.fdatasync(f.fileno())
        f.close()
        os.rename(filename + '~', filename)


    def load(self, filename=None, sync=False):
        """
        Load values from a config file previously saved for this schema.

        :param filename: filename to load values from; if None, will use the
                          :attr:`~kaa.config.Config.filename` property.
        :type filename: str
        :param sync: if True, will overwrite the current file (retaining previous
                     values, of course) if the schema has changed, or create the
                     config file if it does not exist.  (Default: False)
        :type sync: bool

        If no filename has been previously set with the :attr:`~kaa.config.Config.filename`
        property then the ``filename`` argument is required, and in that case the
        filename property will be set to this value.
        """
        local_encoding = get_encoding()
        if filename:
            filename = os.path.expanduser(filename)
        if not filename:
            if not self._filename:
                raise ValueError("Filename not specified and no default filename set.")
            filename = self._filename
        if not self._filename:
            self._filename = filename

        line_regexp = re.compile('^([a-zA-Z0-9_-]+|\[.*?\]|\.)+ *= *(.*)')
        key_regexp = re.compile('(([a-zA-Z0-9_-]+)|(\[.*?\]))')

        self._loaded_hash_schema = None
        self._loaded_hash_value = None

        if not os.path.isfile(filename):
            # filename not found
            if sync:
                self.save(filename)
            return False

        # Disable autosaving while we load the config file.
        autosave_orig = self.autosave
        self.autosave = False

        f = open(filename)
        for line in f.readlines():
            line = line.strip()
            if line.startswith('# -*- coding:'):
                # a encoding is set in the config file, use it
                try:
                    encoding = line[14:-4]
                    ''.encode(encoding)
                    local_encoding = encoding
                except UnicodeError:
                    # bad encoding, ignore it
                    pass
            elif line.startswith('# -*- hash:'):
                self._loaded_hash_schema = line[12:].rstrip('-* ')

            # convert lines based on local encoding
            line = unicode(line, local_encoding)
            if line.find('#') >= 0:
                line = line[:line.find('#')]
            line = line.strip()
            if not line:
                continue

            # split line in key = value
            m = line_regexp.match(line.strip())
            if not m:
                error = ('Unable to parse the line', line.encode(local_encoding))
                if not error in self._bad_lines:
                    log.warning('%s: %s' % error)
                    self._bad_lines.append(error)
                continue
            value = m.groups()[1]
            if value:
                key = line[:-len(value)].rstrip(' =')
            else:
                key = line.rstrip(' =')
            try:
                keylist = [x[0] for x in key_regexp.findall(key.strip()) if x[0] ]
                object = self
                while len(keylist) > 1:
                    key = keylist.pop(0)
                    if key.startswith('['):
                        object = object[key[1:-1]]
                    else:
                        object = getattr(object, key)
                key = keylist[0]
                value = value.strip()
                if isinstance(object, (Dict, List)):
                    key = key[1:-1]
                    if not key and isinstance(object, List):
                        # Implicit indexing for Lists.
                        key = len(object)
                    object[key] = value
                else:
                    setattr(object, key, value)
            except Exception, e:
                error = (str(e), line.encode(local_encoding))
                if not error in self._bad_lines:
                    log.warning('%s: %s' % error)
                    self._bad_lines.append(error)
        f.close()
        self.autosave = autosave_orig
        self._watch_mtime = os.stat(filename)[stat.ST_MTIME]
        if sync and self._loaded_hash_schema != self._hash(values=False):
            # Schema has changed and sync needed.  Saving will update
            # self._loaded_hash_values
            self.save(filename)
        else:
            self._loaded_hash_values = self._hash(values=True)

        return len(self._bad_lines) == 0


    @property
    def filename(self):
        """
        The current config filename.
        """
        return self._filename

    @filename.setter
    def filename(self, filename):
        self._filename = filename


    @property
    def autosave(self):
        """
        Whether or not changes are automatically save.

        If True, will write the config filename (either previously passed to
        :meth:`~kaa.config.Config.load` or defined by the
        :attr:`~kaa.config.Config.filename` property) 5 seconds after the last
        config value update (or program exit, whichever comes first).
        """
        return self._autosave


    @autosave.setter
    def autosave(self, autosave):
        if autosave and not self._autosave:
            self.add_monitor(WeakCallback(self._config_changed_cb))
        elif not autosave and self._autosave:
            self.remove_monitor(WeakCallback(self._config_changed_cb))
            self._autosave_timer.stop()
        self._autosave = autosave


    def _config_changed_cb(self, name, oldval, newval):
        if self._filename:
            if not self._autosave_timer.active:
                main.signals['exit'].connect(self.save)
            # Start/restart the timer to save in 5 seconds.
            self._autosave_timer.start(5)

    def watch(self, watch = True):
        """
        If argument is True (default), adds a watch to the config file and will
        reload the config if it changes.  If INotify is available, use that,
        otherwise stat the file every 3 seconds.

        If argument is False, disable any watches.
        """
        if watch and not self._inotify:
            try:
                self._inotify = INotify()
            except SystemError:
                pass

        assert(self._filename)
        if self._watch_mtime == 0:
            self.load()

        if not watch and self._watching:
            if self._inotify:
                self._inotify.ignore(self._filename)
            self._watch_timer.stop()
            self._watching = False

        elif watch and not self._watching:
            if self._inotify:
                try:
                    signal = self._inotify.watch(self._filename)
                    signal.connect_weak(self._file_changed)
                except IOError:
                    # Adding watch failed, use timer to wait for file to appear.
                    self._watch_timer.start(3)
            else:
                self._watch_timer.start(3)

            self._watching = True


    def _check_file_changed(self):
        try:
            mtime = os.stat(self._filename)[stat.ST_MTIME]
        except (OSError, IOError):
            # Config file not available.
            return

        if self._inotify:
            # Config file is now available, stop this timer and add INotify
            # watch.
            self.watch(False)
            self.watch()

        if mtime != self._watch_mtime:
            return self._file_changed(INotify.MODIFY, self._filename)


    def _file_changed(self, mask, path):
        if mask & INotify.MODIFY:
            # Config file changed.  Attach a monitor so we can keep track of
            # any values that actually changed.
            changed_names = []
            cb = Callback(lambda *args: changed_names.append(args[0]))
            self.add_monitor(cb)
            self.load()
            log.info('Config file %s modified; %d settings changed.' % (self._filename, len(changed_names)))
            log.debug('What changed: %s', ', '.join(changed_names) or 'nothing')
            self.remove_monitor(cb)
        elif mask & (INotify.IGNORED | INotify.MOVE_SELF):
            # File may have been replaced, check mtime now.
            WeakOneShotTimer(self._check_file_changed).start(0.1)
            # Add a slower timer in case it doesn't reappear right away.
            self._watch_timer.start(3)


def set_default(var, value):
    """
    Set default value for the given config variable (proxy).
    """
    if isinstance(var, VarProxy):
        var._item._cfg_set(value, default = True)


def get_default(var):
    if isinstance(var, VarProxy):
        return var._item._default


def get_description(var):
    """
    Get the description for the given config variable or group.
    """
    if isinstance(var, (Group, Dict)):
        return var._desc
    elif isinstance(var, VarProxy):
        return var._item._desc


def get_type(var):
    """
    Returns the type of the given config variable.
    """
    if isinstance(var, VarProxy):
        return var._item._type
    return type(var)


def get_config(filename, module = None):
    """
    Returns a Config object representing the config file provided in
    'filenane'.  If module is None, the specified config file must have the
    module specified (in the "-*- module: ... -*-" metadata), otherwise the
    supplied module (string) is used.  The module must be importable.

    If the config module cannot be determined and one is not specified,
    will raise ValueError.  If import fails, will raise ImportError.
    Otherwise will return the Config object.
    """
    filename = os.path.expanduser(filename)

    if not module:
        # No module specified, check the config file.
        metadata = file(filename).read(256)
        m = re.search(r'^# -\*- module: (\S+) -\*-$', metadata, re.M)
        if m:
            module = m.group(1)
        else:
            raise ValueError, 'No module specified in config file'

    components = module.split('.')
    attr = components.pop()
    module = '.'.join(components)
    try:
        exec('import %s as module' % module)
    except Exception, e:
        log.exception('config loader')
        raise ImportError, 'Could not import config module %s' % module

    config = getattr(module, attr)
    if config._filename and os.path.realpath(config._filename) != os.path.realpath(filename):
        # Existing config object represents a different config file,
        # so must copy.
        config = config.copy()

    config.load(filename)
    return config
