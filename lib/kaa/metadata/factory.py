# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# factory.py
# -----------------------------------------------------------------------------
# $Id: factory.py 4105 2009-05-27 17:16:35Z tack $
#
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------

__all__ = [ 'Factory', 'register', 'gettype', 'parse' ]

# python imports
import stat
import os
import sys
import urlparse
import urllib
import logging

# kaa imports
import kaa.utils

# kaa.metadata imports
import core

# get logging object
log = logging.getLogger('metadata')

# factory object
_factory = None

# some timing debug
TIME_DEBUG = False

R_MIMETYPE  = 0
R_EXTENSION = 1
R_CLASS     = 2

def register(mimetype, extensions, c, magic=None):
    """
    Register a parser to the factory.
    """
    return Factory().register(mimetype, extensions, c, magic)


def gettype(mimetype, extensions):
    """
    Return parser for mimetype / extensions
    """
    return Factory().get(mimetype,extensions)


def parse(filename, force=True):
    """
    parse a file
    """
    result = Factory().create(filename, force)
    if result:
        result._finalize()
    return result


class NullParser(object):
    def __init__(self, file):
        raise core.ParseError

class File(file):

    def read(self, bytes=-1):
        """
        If the size argument is negative or omitted, read until EOF is
        reached. If more than 5MB is requested, an IOError is
        raised. This should not mappen for kaa.metadata parsers.
        """
        if bytes > 5000000 or (bytes < 0 and os.stat(self.name)[stat.ST_SIZE] - self.tell() > 1000000):
            # reading more than 1MB looks like a bug
            raise IOError('trying to read %s bytes' % bytes)
        return super(File, self).read(bytes)

class _Factory:
    """
    Abstract Factory for the creation of Media instances. The different
    Methods create Media objects by parsing the given medium.
    """
    def __init__(self):
        self.extmap = {}
        self.mimemap = {}
        self.classmap = {}
        self.magicmap = {}
        self.types = []
        self.device_types = []
        self.directory_types = []
        self.stream_types = []


    def get_class(self, name):
        if name not in self.classmap:
            # Import the parser class for the given name.
            try:
                exec('from %s import Parser' % name)
                self.classmap[name] = Parser
            except Exception:
                # Something failed while trying to import this parser.  Rather
                # than bail altogher, just log the error and use NullParser.
                log.exception('Error importing parser %s' % name)
                self.classmap[name] = NullParser

        return self.classmap[name]


    def get_scheme_from_info(self, info):
        if info.__class__.__name__ == 'DVDInfo':
            return 'dvd'
        else:
            return 'file'


    def create_from_file(self, file, force=True):
        """
        create based on the file stream 'file
        """
        # Check extension as a hint
        e = os.path.splitext(file.name)[1].lower()
        parser = None
        if e and e.startswith('.') and e[1:] in self.extmap:
            log.debug("trying ext %s" % e[1:])
            parsers = self.extmap[e[1:]]
            for info in parsers:
                file.seek(0,0)
                try:
                    parser = self.get_class(info[R_CLASS])
                    return parser(file)
                except core.ParseError:
                    pass
                except Exception:
                    log.exception('parse error')

        # Try to find a parser based on the first bytes of the
        # file (magic header). If a magic header is found but the
        # parser failed, no other parser will be tried to speed
        # up parsing of a bunch of files. So magic information should
        # only be set if the parser is very sure
        file.seek(0,0)
        magic = file.read(10)
        for length, magicmap in self.magicmap.items():
            if magic[:length] in magicmap:
                for p in magicmap[magic[:length]]:
                    log.info('Trying %s by magic header', p[R_CLASS])
                    file.seek(0,0)
                    try:
                        parser = self.get_class(p[R_CLASS])
                        return parser(file)
                    except core.ParseError:
                        pass
                    except Exception:
                        log.exception('parse error')
                log.info('Magic header found but parser failed')
                return None

        if not force:
            log.info('No Type found by Extension (%s). Giving up.' % e)
            return None

        log.info('No Type found by Extension (%s). Trying all parsers.' % e)

        for e in self.types:
            if self.get_class(e[R_CLASS]) == parser:
                # We already tried this parser, don't bother again.
                continue
            log.debug('trying %s' % e[R_MIMETYPE])
            file.seek(0,0)
            try:
                return self.get_class(e[R_CLASS])(file)
            except core.ParseError:
                pass
            except Exception:
                log.exception('parser error')
        return None


    def create_from_url(self, url, force=True):
        """
        Create information for urls. This includes file:// and cd://
        """
        split  = urlparse.urlsplit(url)
        scheme = split[0]

        if scheme == 'file':
            (scheme, location, path, query, fragment) = split
            return self.create_from_filename(location+path, force)

        elif scheme == 'cdda':
            r = self.create_from_filename(split[4], force)
            if r:
                r.url = url
            return r

        elif scheme == 'http' and False:
            # This code is deactivated right now. Parsing video data over
            # http is way to slow right now. We need a better way to handle
            # this before activating it again.
            # We will need some more soffisticated and generic construction
            # method for this. Perhaps move file.open stuff into __init__
            # instead of doing it here...
            for e in self.stream_types:
                log.debug('Trying %s' % e[R_MIMETYPE])
                try:
                    return self.get_class(e[R_CLASS])(url)
                except core.ParseError:
                    pass

        elif scheme == 'dvd':
            path = split[2]
            if not path.replace('/', ''):
                return self.create_from_device('/dev/dvd')
            return self.create_from_filename(split[2])

        else:
            (scheme, location, path, query, fragment) = split
            try:
                uhandle = urllib.urlopen(url)
            except IOError:
                # Unsupported URL scheme
                return
            mime = uhandle.info().gettype()
            log.debug("Trying %s" % mime)
            if self.mimemap.has_key(mime):
                try:
                    return self.get_class(self.mimemap[mime][R_CLASS])(file)
                except core.ParseError:
                    pass
            # XXX Todo: Try other types


    def create_from_filename(self, filename, force=True):
        """
        Create information for the given filename
        """
        if os.path.isdir(filename):
            return None
        if os.path.isfile(filename):
            try:
                f = File(filename,'rb')
            except (IOError, OSError), e:
                log.info('error reading %s: %s' % (filename, e))
                return None
            r = self.create_from_file(f, force)
            f.close()
            if r:
                r.url = '%s://%s' % (self.get_scheme_from_info(r), os.path.abspath(filename))
                return r
        return None


    def create_from_device(self,devicename):
        """
        Create information from the device. Currently only rom drives
        are supported.
        """
        for e in self.device_types:
            log.debug('Trying %s' % e[R_MIMETYPE])
            try:
                t = self.get_class(e[R_CLASS])(devicename)
                t.url = '%s://%s' % (self.get_scheme_from_info(t), os.path.abspath(devicename))
                return t
            except core.ParseError:
                pass
        return None


    def create_from_directory(self, dirname):
        """
        Create information from the directory.
        """
        for e in self.directory_types:
            log.debug('Trying %s' % e[R_MIMETYPE])
            try:
                return self.get_class(e[R_CLASS])(dirname)
            except core.ParseError:
                pass
        return None


    def create(self, name, force=True):
        """
        Global 'create' function. This function calls the different
        'create_from_'-functions.
        """
        try:
            if name.find('://') > 0:
                return self.create_from_url(name)
            if not os.path.exists(name):
                return None
            if (os.uname()[0] == 'FreeBSD' and \
                stat.S_ISCHR(os.stat(name)[stat.ST_MODE])) \
                or stat.S_ISBLK(os.stat(name)[stat.ST_MODE]):
                return self.create_from_device(name)
            if os.path.isdir(name):
                return self.create_from_directory(name)
            return self.create_from_filename(name, force)
        except Exception:
            log.exception('kaa.metadata.create error')
            log.warning('Please report this bug to the Freevo mailing list')
            return None



    def register(self, mimetype, extensions, c, magic=None):
        """
        register the parser to kaa.metadata
        """
        log.debug('%s registered' % mimetype)
        tuple = (mimetype, extensions, c)

        if extensions == core.EXTENSION_DEVICE:
            self.device_types.append(tuple)
        elif extensions == core.EXTENSION_DIRECTORY:
            self.directory_types.append(tuple)
        elif extensions == core.EXTENSION_STREAM:
            self.stream_types.append(tuple)
        else:
            self.types.append(tuple)
            for e in (x.lower() for x in extensions):
                if e not in self.extmap:
                    self.extmap[e] = []
                self.extmap[e].append(tuple)
            self.mimemap[mimetype] = tuple

        # add to magic header list
        if magic is not None:
            if not len(magic) in self.magicmap:
                self.magicmap[len(magic)] = {}
            if not magic in self.magicmap[len(magic)]:
                self.magicmap[len(magic)][magic] = []
            self.magicmap[len(magic)][magic].append(tuple)


    def get(self, mimetype, extensions):
        """
        return the object for mimetype/extensions or None
        """
        if extensions == core.EXTENSION_DEVICE:
            l = self.device_types
        elif extensions == core.EXTENSION_DIRECTORY:
            l = self.directory_types
        elif extensions == core.EXTENSION_STREAM:
            l = self.stream_types
        else:
            l = self.types

        for info in l:
            if info[R_MIMETYPE] == mimetype and info[R_EXTENSION] == extensions:
                return self.get_class(info[R_CLASS])
        return None

Factory = kaa.utils.Singleton(_Factory)
