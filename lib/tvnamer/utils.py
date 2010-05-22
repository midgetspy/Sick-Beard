#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Utilities for tvnamer, including filename parsing
"""

import datetime
import os
import re
import sys
import shutil
import logging
import platform

from lib.tvdb_api.tvdb_api import (tvdb_error, tvdb_shownotfound, tvdb_seasonnotfound,
tvdb_episodenotfound, tvdb_attributenotfound, tvdb_userabort)

from unicode_helper import p

from config import Config
from tvnamer_exceptions import (InvalidPath, InvalidFilename,
ShowNotFound, DataRetrievalError, SeasonNotFound, EpisodeNotFound,
EpisodeNameNotFound, ConfigValueError, UserAbort)


def log():
    """Returns the logger for current file
    """
    return logging.getLogger(__name__)


def warn(text):
    """Displays message to sys.stdout
    """
    p(text, file = sys.stderr)


def getEpisodeName(tvdb_instance, episode):
    """Queries the tvdb_api.Tvdb instance for episode name and corrected
    series name.
    If series cannot be found, it will warn the user. If the episode is not
    found, it will use the corrected show name and not set an episode name.
    If the site is unreachable, it will warn the user. If the user aborts
    it will catch tvdb_api's user abort error and raise tvnamer's
    """
    try:
        show = tvdb_instance[episode.seriesname]
    except tvdb_error, errormsg:
        raise DataRetrievalError("Error contacting www.thetvdb.com: %s" % errormsg)
    except tvdb_shownotfound:
        # No such series found.
        raise ShowNotFound("Show %s not found on www.thetvdb.com" % episode.seriesname)
    except tvdb_userabort, error:
        raise UserAbort(unicode(error))
    else:
        # Series was found, use corrected series name
        correctedShowName = show['seriesname']

    if episode.seasonnumber == -1:
        # Date-based episode
        epnames = []
        for cepno in episode.episodenumbers:
            try:
                sr = show.airedOn(cepno)
                if len(sr) > 1:
                    raise EpisodeNotFound(
                        "Ambigious air date %s, there were %s episodes on that day" % (
                        cepno, len(sr)))
                epnames.append(sr[0]['episodename'])
            except tvdb_episodenotfound:
                raise EpisodeNotFound(
                    "Episode that aired on %s could not be found" % (
                    cepno))
        return correctedShowName, epnames

    if episode.seasonnumber is None:
        # Series without concept of seasons have all episodes in season 1
        seasonnumber = 1
    else:
        seasonnumber = episode.seasonnumber

    epnames = []
    for cepno in episode.episodenumbers:
        try:
            episodeinfo = show[seasonnumber][cepno]

        except tvdb_seasonnotfound:
            raise SeasonNotFound(
                "Season %s of show %s could not be found" % (
                episode.seasonnumber,
                episode.seriesname))

        except tvdb_episodenotfound:
            raise EpisodeNotFound(
                "Episode %s of show %s, season %s could not be found" % (
                    cepno,
                    episode.seriesname,
                    episode.seasonnumber))

        except tvdb_attributenotfound:
            raise EpisodeNameNotFound(
                "Could not find episode name for %s" % episode)
        else:
            epnames.append(episodeinfo['episodename'])

    return correctedShowName, epnames


def _applyReplacements(cfile, replacements):
    """Applies custom replacements.

    Argument cfile is string.

    Argument replacements is a list of dicts, with keys "match",
    "replacement", and (optional) "is_regex"
    """
    for rep in replacements:
        if 'is_regex' in rep and rep['is_regex']:
            cfile = re.sub(rep['match'], rep['replacement'], cfile)
        else:
            cfile = cfile.replace(rep['match'], rep['replacement'])

    return cfile


def applyCustomInputReplacements(cfile):
    """Applies custom input filename replacements, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['input_filename_replacements'])


def applyCustomOutputReplacements(cfile):
    """Applies custom output filename replacements, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['output_filename_replacements'])


def applyCustomFullpathReplacements(cfile):
    """Applies custom replacements to full path, wraps _applyReplacements
    """
    return _applyReplacements(cfile, Config['move_files_fullpath_replacements'])


def cleanRegexedSeriesName(seriesname):
    """Cleans up series name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:

    >>> cleanRegexedSeriesName("an.example.1.0.test")
    'an example 1.0 test'
    >>> cleanRegexedSeriesName("an_example_1.0_test")
    'an example 1.0 test'
    """
    seriesname = re.sub("(\D)[.](\D)", "\\1 \\2", seriesname)
    seriesname = re.sub("(\D)[.]", "\\1 ", seriesname)
    seriesname = re.sub("[.](\D)", " \\1", seriesname)
    seriesname = seriesname.replace("_", " ")
    seriesname = re.sub("-$", "", seriesname)
    return seriesname.strip()


class FileFinder(object):
    """Given a file, it will verify it exists. Given a folder it will descend
    one level into it and return a list of files, unless the recursive argument
    is True, in which case it finds all files contained within the path.

    The with_extension argument is a list of valid extensions, without leading
    spaces. If an empty list (or None) is supplied, no extension checking is
    performed.
    """

    def __init__(self, path, with_extension = None, recursive = False):
        self.path = path
        if with_extension is None:
            self.with_extension = []
        else:
            self.with_extension = with_extension
        self.recursive = recursive

    def findFiles(self):
        """Returns list of files found at path
        """
        if os.path.isfile(self.path):
            if self._checkExtension(self.path):
                return [os.path.abspath(self.path)]
            else:
                return []
        elif os.path.isdir(self.path):
            return self._findFilesInPath(self.path)
        else:
            raise InvalidPath("%s is not a valid file/directory" % self.path)

    def _checkExtension(self, fname):
        if len(self.with_extension) == 0:
            return True

        _, extension = os.path.splitext(fname)
        for cext in self.with_extension:
            cext = ".%s" % cext
            if extension == cext:
                return True
        else:
            return False

    def _findFilesInPath(self, startpath):
        """Finds files from startpath, could be called recursively
        """
        allfiles = []
        for subf in os.listdir(unicode(startpath)):
            if not self._checkExtension(subf):
                continue
            newpath = os.path.join(startpath, subf)
            newpath = os.path.abspath(newpath)
            if os.path.isfile(newpath):
                allfiles.append(newpath)
            else:
                if self.recursive:
                    allfiles.extend(self._findFilesInPath(newpath))
                #end if recursive
            #end if isfile
        #end for sf
        return allfiles


class FileParser(object):
    """Deals with parsing of filenames
    """

    def __init__(self, path):
        self.path = path
        self.compiled_regexs = []
        self._compileRegexs()

    def _compileRegexs(self):
        """Takes episode_patterns from config, compiles them all
        into self.compiled_regexs
        """
        for cpattern in Config['filename_patterns']:
            try:
                cregex = re.compile(cpattern, re.VERBOSE)
            except re.error, errormsg:
                warn("WARNING: Invalid episode_pattern, %s. %s" % (
                    errormsg, cregex.pattern))
            else:
                self.compiled_regexs.append(cregex)

    def parse(self):
        """Runs path via configured regex, extracting data from groups.
        Returns an EpisodeInfo instance containing extracted data.
        """
        _, filename = os.path.split(self.path)

        filename = applyCustomInputReplacements(filename)

        for cmatcher in self.compiled_regexs:
            match = cmatcher.match(filename)
            if match:
                namedgroups = match.groupdict().keys()

                if 'episodenumber1' in namedgroups:
                    # Multiple episodes, have episodenumber1 or 2 etc
                    epnos = []
                    for cur in namedgroups:
                        epnomatch = re.match('episodenumber(\d+)', cur)
                        if epnomatch:
                            epnos.append(int(match.group(cur)))
                    epnos.sort()
                    episodenumbers = epnos

                elif 'episodenumberstart' in namedgroups:
                    # Multiple episodes, regex specifies start and end number
                    start = int(match.group('episodenumberstart'))
                    end = int(match.group('episodenumberend'))
                    if start > end:
                        # Swap start and end
                        start, end = end, start
                    episodenumbers = range(start, end + 1)

                elif 'episodenumber' in namedgroups:
                    episodenumbers = [int(match.group('episodenumber')), ]

                elif 'year' in namedgroups or 'month' in namedgroups or 'day' in namedgroups:
                    if not all(['year' in namedgroups, 'month' in namedgroups, 'day' in namedgroups]):
                        raise ConfigValueError(
                            "Date-based regex must contain groups 'year', 'month' and 'day'")
                    match.group('year')

                    episodenumbers = [datetime.date(int(match.group('year')),
                                                    int(match.group('month')),
                                                    int(match.group('day')))]

                else:
                    raise ConfigValueError(
                        "Regex does not contain episode number group, should"
                        "contain episodenumber, episodenumber1-9, or"
                        "episodenumberstart and episodenumberend\n\nPattern"
                        "was:\n" + cmatcher.pattern)

                if 'seasonnumber' in namedgroups:
                    seasonnumber = int(match.group('seasonnumber'))
                elif 'year' in namedgroups and 'month' in namedgroups and 'day' in namedgroups:
                    seasonnumber = -1
                else:
                    # No season number specified, usually for Anime
                    seasonnumber = None

                if 'seriesname' in namedgroups:
                    seriesname = match.group('seriesname')
                else:
                    raise ConfigValueError(
                        "Regex must contain seriesname. Pattern was:\n" + cmatcher.pattern)

                if seriesname != None:
                    seriesname = cleanRegexedSeriesName(seriesname)

                episode = EpisodeInfo(
                    seriesname = seriesname,
                    seasonnumber = seasonnumber,
                    episodenumbers = episodenumbers,
                    filename = self.path)
                return episode
        else:
            raise InvalidFilename(self.path)


def formatEpisodeName(names, join_with):
    """Takes a list of episode names, formats them into a string.
    If two names are supplied, such as "Pilot (1)" and "Pilot (2)", the
    returned string will be "Pilot (1-2)"

    If two different episode names are found, such as "The first", and
    "Something else" it will return "The first, Something else"
    """
    if len(names) == 1:
        return names[0]

    found_names = []
    numbers = []
    for cname in names:
        number = re.match("(.*) \(([0-9]+)\)$", cname)
        if number:
            epname, epno = number.group(1), number.group(2)
            if len(found_names) > 0 and epname not in found_names:
                return join_with.join(names)
            found_names.append(epname)
            numbers.append(int(epno))
        else:
            # An episode didn't match
            return join_with.join(names)

    names = []
    start, end = min(numbers), max(numbers)
    names.append("%s (%d-%d)" % (found_names[0], start, end))
    return join_with.join(names)


def makeValidFilename(value, normalize_unicode = False, windows_safe = False, custom_blacklist = None, replace_with = "_"):
    """
    Takes a string and makes it into a valid filename.

    normalize_unicode replaces accented characters with ASCII equivalent, and
    removes characters that cannot be converted sensibly to ASCII.

    windows_safe forces Windows-safe filenames, regardless of current platform

    custom_blacklist specifies additional characters that will removed. This
    will not touch the extension separator:

        >>> makeValidFilename("T.est.avi", custom_blacklist=".")
        'T_est.avi'
    """

    if windows_safe:
        # Allow user to make Windows-safe filenames, if they so choose
        sysname = "Windows"
    else:
        sysname = platform.system()

    # If the filename starts with a . prepend it with an underscore, so it
    # doesn't become hidden.

    # This is done before calling splitext to handle filename of "."
    # splitext acts differently in python 2.5 and 2.6 - 2.5 returns ('', '.')
    # and 2.6 returns ('.', ''), so rather than special case '.', this
    # special-cases all files starting with "." equally (since dotfiles have)
    if value.startswith("."):
        value = "_" + value

    # Treat extension seperatly
    value, extension = os.path.splitext(value)

    # Remove any null bytes
    value = value.replace("\0", "")

    # Blacklist of characters
    if sysname == 'Darwin':
        # : is technically allowed, but Finder will treat it as / and will
        # generally cause weird behaviour, so treat it as invalid.
        blacklist = r"/:"
    elif sysname in ['Linux', 'FreeBSD']:
        blacklist = r"/"
    else:
        # platform.system docs say it could also return "Windows" or "Java".
        # Failsafe and use Windows sanitisation for Java, as it could be any
        # operating system.
        blacklist = r"\/:*?\"<>|"

    # Append custom blacklisted characters
    if custom_blacklist is not None:
        blacklist += custom_blacklist

    # Replace every blacklisted character with a underscore
    value = re.sub("[%s]" % re.escape(blacklist), replace_with, value)

    # Remove any trailing whitespace
    value = value.strip()

    # There are a bunch of filenames that are not allowed on Windows.
    # As with character blacklist, treat non Darwin/Linux platforms as Windows
    if sysname not in ['Darwin', 'Linux']:
        invalid_filenames = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2",
        "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1",
        "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
        if value in invalid_filenames:
            value = "_" + value

    # Replace accented characters with ASCII equivalent
    if normalize_unicode:
        import unicodedata
        value = unicode(value) # cast data to unicode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')

    # Truncate filenames to valid/sane length.
    # NTFS is limited to 255 characters, HFS+ and EXT3 don't seem to have
    # limits, FAT32 is 254. I doubt anyone will take issue with losing that
    # one possible character, and files over 254 are pointlessly unweidly
    max_len = 254

    if len(value + extension) > max_len:
        if len(extension) > len(value):
            # Truncate extension instead of filename, no extension should be
            # this long..
            new_length = max_len - len(value)
            extension = extension[:new_length]
        else:
            new_length = max_len - len(extension)
            value = value[:new_length]

    return value + extension


def formatEpisodeNumbers(episodenumbers):
    """Format episode number(s) into string, using configured values
    """
    if len(episodenumbers) == 1:
        epno = Config['episode_single'] % episodenumbers[0]
    else:
        epno = Config['episode_separator'].join(
            Config['episode_single'] % x for x in episodenumbers)

    return epno

class EpisodeInfo(object):
    """Stores information (season, episode number, episode name), and contains
    logic to generate new name
    """

    def __init__(self,
        seriesname = None,
        seasonnumber = None,
        episodenumbers= None,
        episodename = None,
        filename = None):

        self.seriesname = seriesname
        self.seasonnumber = seasonnumber
        self.episodenumbers = episodenumbers
        self.episodename = episodename
        self.fullpath = filename

    def fullpath_get(self):
        return self._fullpath

    def fullpath_set(self, value):
        self._fullpath = value
        if value is None:
            self.filename, self.extension = None, None
        else:
            self.filepath, self.filename = os.path.split(value)
            self.filename, self.extension = os.path.splitext(self.filename)
            self.extension = self.extension.replace(".", "")

    fullpath = property(fullpath_get, fullpath_set)

    @property
    def fullfilename(self):
        return u"%s.%s" % (self.filename, self.extension)

    def generateFilename(self):
        """
        Uses the following config options:
        filename_with_episode # Filename when episode name is found
        filename_without_episode # Filename when no episode can be found
        episode_single # formatting for a single episode number
        episode_separator # used to join multiple episode numbers
        """
        # Format episode number into string, or a list
        if self.seasonnumber != -1:
            epno = formatEpisodeNumbers(self.episodenumbers)
        else:
            epno = str(self.episodenumbers[0])

        # Data made available to config'd output file format
        if self.extension is None:
            prep_extension = ''
        else:
            prep_extension = '.%s' % self.extension

        epdata = {
            'seriesname': self.seriesname,
            'seasonno': self.seasonnumber,
            'episode': epno,
            'episodename': self.episodename,
            'ext': prep_extension}

        if self.episodename is None:
            if self.seasonnumber is None:
                fname = Config['filename_without_episode_no_season'] % epdata
            elif self.seasonnumber == -1:
                fname = Config['filename_with_date_without_episode'] % epdata
            else:
                fname = Config['filename_without_episode'] % epdata
        else:
            if isinstance(self.episodename, list):
                epdata['episodename'] = formatEpisodeName(
                    self.episodename,
                    join_with = Config['multiep_join_name_with']
                )

            if self.seasonnumber is None:
                fname = Config['filename_with_episode_no_season'] % epdata
            elif self.seasonnumber == -1:
                fname = Config['filename_with_date_and_episode'] % epdata
            else:
                fname = Config['filename_with_episode'] % epdata

        return makeValidFilename(
            fname,
            normalize_unicode = Config['normalize_unicode_filenames'],
            windows_safe = Config['windows_safe_filenames'],
            replace_with = Config['replace_invalid_characters_with'])

    def __repr__(self):
        return "<%s: %s>" % (
            self.__class__.__name__,
            self.generateFilename())


def same_partition(f1, f2):
    """Returns True if both files or directories are on the same partition
    """
    return os.stat(f1).st_dev == os.stat(f2).st_dev


def delete_file(fpath):
    raise NotImplementedError("delete_file not yet implimented")


class Renamer(object):
    """Deals with renaming of files
    """

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)

    def newName(self, newName, force = False):
        """Renames a file, keeping the path the same.
        """
        filepath, filename = os.path.split(self.filename)
        filename, _ = os.path.splitext(filename)

        newpath = os.path.join(filepath, newName)

        if os.path.isfile(newpath):
            # If the destination exists, raise exception unless force is True
            if not force:
                raise OSError("File %s already exists, not forcefully renaming %s" % (
                    newpath, self.filename))

        os.rename(self.filename, newpath)
        self.filename = newpath

    def newPath(self, new_path, force = False, always_copy = False, always_move = False, create_dirs = True, getPathPreview = False):
        """Moves the file to a new path.

        If it is on the same partition, it will be moved (unless always_copy is True)
        If it is on a different partition, it will be copied.
        If the target file already exists, it will raise OSError unless force is True.
        """

        if always_copy and always_move:
            raise ValueError("Both always_copy and always_move cannot be specified")

        old_dir, old_filename = os.path.split(self.filename)

        # Join new filepath to old one (to handle realtive dirs)
        new_dir = os.path.abspath(os.path.join(old_dir, new_path))

        # Join new filename onto new filepath
        new_fullpath = os.path.join(new_dir, old_filename)

        if len(Config['move_files_fullpath_replacements']) > 0:
            p("Before custom full path replacements: %s" % (new_fullpath))
            new_fullpath = applyCustomFullpathReplacements(new_fullpath)
            new_dir = os.path.dirname(new_fullpath)

        p("New path: %s" % new_fullpath)

        if getPathPreview:
            return new_fullpath

        if create_dirs:
            p("Creating %s" % new_dir)
            try:
                os.makedirs(new_dir)
            except OSError, e:
                if e.errno != 17:
                    raise

        if os.path.isfile(new_fullpath):
            # If the destination exists, raise exception unless force is True
            if not force:
                raise OSError("File %s already exists, not forcefully moving %s" % (
                    new_fullpath, self.filename))

        if same_partition(self.filename, new_dir):
            if always_copy:
                # Same partition, but forced to copy
                p("copy %s to %s" % (self.filename, new_fullpath))
                shutil.copyfile(self.filename, new_fullpath)
            else:
                # Same partition, just rename the file to move it
                p("move %s to %s" % (self.filename, new_fullpath))
                os.rename(self.filename, new_fullpath)
        else:
            # File is on different partition (different disc), copy it
            p("copy %s to %s" % (self.filename, new_fullpath))
            shutil.copyfile(self.filename, new_fullpath)
            if always_move:
                # Forced to move file, we just trash old file
                p("Deleting %s" % (self.filename))
                delete_file(self.filename)

        self.filename = new_fullpath
