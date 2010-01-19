#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Holds Config singleton
"""

import os
import xml
import xml.etree.ElementTree as ET

from tvnamer_exceptions import InvalidConfigFile, WrongConfigVersion


def _serialiseElement(root, name, elem, etype='option'):
    """Used for config XML saving, currently supports strings, integers
    and lists contains the any of these
    """
    celem = ET.SubElement(root, etype)
    if name is not None:
        celem.set('name', name)

    if isinstance(elem, bool):
        celem.set('type', 'bool')
        celem.text = str(elem)
        return
    elif isinstance(elem, int):
        celem.set('type', 'int')
        celem.text = str(elem)
        return
    elif isinstance(elem, basestring):
        celem.set('type', 'string')
        celem.text = elem
        return
    elif isinstance(elem, list):
        celem.set('type', 'list')
        for subelem in elem:
            _serialiseElement(celem, None, subelem, 'value')
        return
    elif elem is None:
        celem.set('type', 'None')
        celem.text = 'None'
    else:
        raise ValueError("Element %r (type: %s) could not be serialised" % (
            elem,
            type(elem)))


def _deserialiseItem(ctype, citem):
    """Used for config XML loading, currently supports strings, integers
    and lists contains the any of these
    """
    if ctype == 'int':
        return int(citem.text)
    elif ctype == 'string':
        if citem.text is None:
            # Empty string is serialised as None, rather than an empty string
            return ""
        else:
            return citem.text
    elif ctype == 'bool':
        if citem.text == 'True':
            return True
        elif citem.text == 'False':
            return False
        else:
            raise InvalidConfigFile(
                "Boolean value for %s was not 'True' or ', was %r" % (
                    citem.text))
    elif ctype == 'None':
        return None
    elif ctype == 'list':
        ret = []
        for subitem in citem:
            ret.append(_deserialiseItem(subitem.attrib['type'], subitem))
        return ret
    else:
        raise ValueError("Element %r (type: %s) could not be deserialised" % (
            citem,
            ctype))


def _indentTree(elem, level=0):
    """Inline-modification of ElementTree to "pretty-print" the XML
    """
    i = "\n" + "    "*level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            _indentTree(child, level+1)
        lastchild = elem[-1]
        if not lastchild.tail or not lastchild.tail.strip():
            lastchild.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class _ConfigManager(dict):
    """Stores configuration options, deals with optional parsing and saving
    of options to disc.
    """

    VERSION = 1
    DEFAULT_CONFIG_FILE = os.path.expanduser("~/.tvnamer.xml")

    def __init__(self):
        super(_ConfigManager, self).__init__(self)
        if os.path.isfile(self.DEFAULT_CONFIG_FILE):
            self.loadConfig(self.DEFAULT_CONFIG_FILE)
        else:
            self.useDefaultConfig()

    def _setDefaults(self):
        """If no config file is found, these are used. If the config file
        skips any options, the missing settings are set to the defaults.
        """
        defaults = {
            'selectfirst': False,
            'alwaysrename': False,
            'verbose': False,
            'recursive': False,
            'windows_safe_filenames': False,
            'normalize_unicode_filenames': False,
            'custom_filename_character_blacklist': '',
            'replace_blacklisted_characters_with': '_',
            'multiep_join_name_with': ', ',
            'language': 'en',
            'search_all_languages': True,

            'episode_patterns': [
                # [group] Show - 01-02 [Etc]
                '''^\[.+?\][ ]? # group name
                (?P<seriesname>.*?)[ ]?[-_][ ]? # show name, padding, spaces?
                (?P<episodenumberstart>\d+)   # first episode number
                ([-_]\d+)*                    # optional repeating episodes
                [-_](?P<episodenumberend>\d+) # last episode number
                [^\/]*$''',

                # [group] Show - 01 [Etc]
                '''^\[.+?\][ ]? # group name
                (?P<seriesname>.*) # show name
                [ ]?[-_][ ]?(?P<episodenumber>\d+)
                [^\/]*$''',

                # foo.s01e23e24*
                '''
                ^(?P<seriesname>.+?)[ \._\-]             # show name
                [Ss](?P<seasonnumber>[0-9]+)             # s01
                [\.\- ]?                                 # separator
                [Ee](?P<episodenumberstart>[0-9]+)       # first e23
                ([\.\- ]?                                # separator
                [Ee][0-9]+)*                             # e24e25 etc
                [\.\- ]?[Ee](?P<episodenumberend>[0-9]+) # final episode num
                [^\/]*$''',

                # foo.1x23x24*
                '''
                ^(?P<seriesname>.+?)[ \._\-]             # show name
                (?P<seasonnumber>[0-9]+)                 # 1
                x(?P<episodenumberstart>[0-9]+)          # first x23
                (x[0-9]+)*                               # x24x25 etc
                x(?P<episodenumberend>[0-9]+)            # final episode num
                [^\/]*$''',

                # foo.s01e23-24*
                '''
                ^(?P<seriesname>.+?)[ \._\-]             # show name
                [Ss](?P<seasonnumber>[0-9]+)             # s01
                [\.\- ]?                                 # separator
                [Ee](?P<episodenumberstart>[0-9]+)       # first e23
                (                                        # -24 etc
                     [\-]
                     [Ee]?[0-9]+
                )*
                     [\-]                                # separator
                     (?P<episodenumberend>[0-9]+)        # final episode num
                [^\/]*$''',

                # foo.1x23-24*
                '''
                ^(?P<seriesname>.+?)[ \._\-]             # show name
                (?P<seasonnumber>[0-9]+)                 # 1
                x(?P<episodenumberstart>[0-9]+)          # first x23
                (                                        # -24 etc
                     [\-][0-9]+
                )*
                     [\-]                                # separator
                     (?P<episodenumberend>[0-9]+)        # final episode num
                [^\/]*$''',

                # foo.[1x09-11]*
                '''^(?P<seriesname>.+?)[ \._\-]       # show name and padding
                \[                                  # [
                    ?(?P<seasonnumber>[0-9]+)       # season
                x                                   # x
                    (?P<episodenumberstart>[0-9]+)  # episode
                    (- [0-9]+)*
                -                                   # -
                    (?P<episodenumberend>[0-9]+)    # episode
                \]                                  # \]
                [^\\/]*$''',

                # foo.s0101, foo.0201
                '''^(?P<seriesname>.+?)[ \._\-]
                [Ss](?P<seasonnumber>[0-9]{2})
                [\.\- ]?
                (?P<episodenumber>[0-9]{2})
                [^\\/]*$''',

                # foo.1x09*
                '''^(?P<seriesname>.+?)[ \._\-]       # show name and padding
                \[?                                 # [ optional
                (?P<seasonnumber>[0-9]+)            # season
                x                                   # x
                (?P<episodenumber>[0-9]+)           # episode
                \]?                                 # ] optional
                [^\\/]*$''',

                # foo.s01.e01, foo.s01_e01
                '''^(?P<seriesname>.+?)[ \._\-]
                [Ss](?P<seasonnumber>[0-9]+)[\.\- ]?
                [Ee]?(?P<episodenumber>[0-9]+)
                [^\\/]*$''',

                # foo.103*
                '''^(?P<seriesname>.+)[ \._\-]
                (?P<seasonnumber>[0-9]{1})
                (?P<episodenumber>[0-9]{2})
                [\._ -][^\\/]*$''',

                # foo.0103*
                '''^(?P<seriesname>.+)[ \._\-]
                (?P<seasonnumber>[0-9]{2})
                (?P<episodenumber>[0-9]{2,3})
                [\._ -][^\\/]*$''',

                # show.name.e123.abc
                '''^(?P<seriesname>.+?)          # Show name
                [ \._\-]                       # Padding
                [Ee](?P<episodenumber>[0-9]+)  # E123
                [\._ -][^\\/]*$                # More padding, then anything
                '''
            ],

            'filename_with_episode':
             '%(seriesname)s - [%(seasonno)02dx%(episode)s] - %(episodename)s%(ext)s',
            'filename_without_episode':
             '%(seriesname)s - [%(seasonno)02dx%(episode)s]%(ext)s',
             'filename_with_episode_no_season':
              '%(seriesname)s - [%(episode)s] - %(episodename)s%(ext)s',
             'filename_without_episode_no_season':
              '%(seriesname)s - [%(episode)s]%(ext)s',

            'episode_single': '%02d',
            'episode_separator': '-'}

        # Updates defaults dict with current settings
        for dkey, dvalue in defaults.items():
            self.setdefault(dkey, dvalue)

    def _clearConfig(self):
        """Clears all config options, usually before loading a new config file
        """
        self.clear()

    def _parseConfigString(self, xmlsrc):
        """Loads a config from a file
        """
        try:
            root = ET.fromstring(xmlsrc)
        except xml.parsers.expat.ExpatError, errormsg:
            raise InvalidConfigFile(errormsg)

        version = int(root.attrib['version'])
        if version != 1:
            raise WrongConfigVersion(
                'Expected version %d, got version %d' % (
                    self.VERSION, version))

        conf = {}
        for citem in root:
            value = _deserialiseItem(citem.attrib['type'], citem)
            conf[citem.attrib['name']] = value

        return conf

    def _saveConfig(self, configdict):
        """Takes a config dictionary, returns XML as string
        """
        root = ET.Element('tvnamer')
        root.set('version', str(self.VERSION))

        for ckey, cvalue in sorted(configdict.items()):
            _serialiseElement(root, ckey, cvalue)

        _indentTree(root)
        return ET.tostring(root).strip()

    def loadConfig(self, filename):
        """Use Config.loadFile("something") to load a new config files, clears
        all existing options
        """
        self._clearConfig()
        try:
            xmlsrc = open(filename).read()
        except IOError, errormsg:
            raise InvalidConfigFile(errormsg)
        else:
            loaded_conf = self._parseConfigString(xmlsrc)
            self._setDefaults() # Makes sure all config options are set
            self.update(loaded_conf)

    def saveConfig(self, filename):
        """Stores config options into a file
        """
        xmlsrc = self._saveConfig(self)
        try:
            fhandle = open(filename, 'w')
        except IOError, errormsg:
            raise InvalidConfigFile(errormsg)
        else:
            fhandle.write(xmlsrc)
            fhandle.close()

    def useDefaultConfig(self):
        """Uses only the default settings, works similarly to Config.loadFile
        """
        self._clearConfig()
        self._setDefaults()


Config = _ConfigManager()
