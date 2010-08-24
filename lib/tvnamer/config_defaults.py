#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Holds default config values
"""

defaults = {
    # Select first series search result
    'select_first': False,

    # Always rename files
    'always_rename': False,

    # Batch (same as select_first and always_rename)
    'batch': False,

    # Fail if error finding show data (thetvdb.com is down etc)
    # Only functions when always_rename is True
    'skip_file_on_error': True,

    # Verbose mode (debugging info)
    'verbose': False,

    # Recurse more than one level into folders. When False, only
    # desends one level.
    'recursive': False,

    # When non-empty, only look for files with this extension.
    # No leading dot, for example: ['avi', 'mkv', 'mp4']
    'valid_extensions': [],

    # Force Windows safe filenames (always True on Windows)
    'windows_safe_filenames': False,

    # Replace accented unicode characters with ASCII equivalents,
    # removing characters than can't be translated.
    'normalize_unicode_filenames': False,

    # Replacement characters for invalid filename characters
    'replace_invalid_characters_with': '_',

    # Replacements performed on input file before parsing.
    'input_filename_replacements': [
    ],

    # Replacements performed on files after the new name is generated.
    'output_filename_replacements': [
    ],

    # Replacements are performed on the full path used by move_files feature,
    # including the filename
    'move_files_fullpath_replacements': [
    ],

    # Language to (try) and retrieve episode data in
    'language': 'en',

    # Search in all possible languages
    'search_all_languages': True,

    # Move renamed files to directory?
    'move_files_enable': False,

    # Seperation confirmation of moving or copying renamed file?
    # If False, will move files when renaming.
    'move_files_confirmation': True,

    # Destination to move files to. Trailing slash is not necessary.
    # Use forward slashes, even on Windows. Realtive paths are realtive to
    # the existing file's path (not current working dir). A value of '.' will
    # not move the file anywhere.
    #
    # Use Python's string formatting to add dynamic paths. Available variables:
    # - %(seriesname)s
    # - %(seasonnumber)d
    # - %(episodenumbers)s (Note: this is a string, formatted with config
    #                       variable episode_single and joined with episode_separator)
    'move_files_destination': '.',

    # Patterns to parse input filenames with
    'filename_patterns': [
        # [group] Show - 01-02 [Etc]
        '''^\[.+?\][ ]? # group name
        (?P<seriesname>.*?)[ ]?[-_][ ]?          # show name, padding, spaces?
        (?P<episodenumberstart>\d+)              # first episode number
        ([-_]\d+)*                               # optional repeating episodes
        [-_](?P<episodenumberend>\d+)            # last episode number
        [^\/]*$''',

        # [group] Show - 01 [Etc]
        '''^\[.+?\][ ]? # group name
        (?P<seriesname>.*) # show name
        [ ]?[-_][ ]?(?P<episodenumber>\d+)
        [^\/]*$''',

        # foo s01e23 s01e24 s01e25 *
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        ([\.\- ]+                                # separator
        [Ss](?P=seasonnumber)                    # s01
        [\.\- ]?                                 # separator
        [Ee][0-9]+)*                             # e24 etc (middle groups)
        ([\.\- ]+                                # separator
        [Ss](?P=seasonnumber)                    # last s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberend>[0-9]+))        # final episode number
        ([\.\-\ ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # foo.s01e23e24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        ([\.\- ]?                                # separator
        [Ee][0-9]+)*                             # e24e25 etc
        [\.\- ]?[Ee](?P<episodenumberend>[0-9]+) # final episode num
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # foo.1x23 1x24 1x25
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # first season number (1)
        [xX](?P<episodenumberstart>[0-9]+)       # first episode (x23)
        ([ \._\-]+                               # separator
        (?P=seasonnumber)                        # more season numbers (1)
        [xX][0-9]+)*                             # more episode numbers (x24)
        ([ \._\-]+                               # separator
        (?P=seasonnumber)                        # last season number (1)
        [xX](?P<episodenumberend>[0-9]+))        # last episode number (x25)
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # foo.1x23x24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # 1
        [xX](?P<episodenumberstart>[0-9]+)       # first x23
        ([xX][0-9]+)*                            # x24x25 etc
        [xX](?P<episodenumberend>[0-9]+)         # final episode num
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # foo.s01e23-24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        [Ss](?P<seasonnumber>[0-9]+)             # s01
        [\.\- ]?                                 # separator
        [Ee](?P<episodenumberstart>[0-9]+)       # first e23
        (                                        # -24 etc
             [\-]
             [Ee]?[0-9]+
        )*
             [\-]                                # separator
             [Ee]?(?P<episodenumberend>[0-9]+)   # final episode num
        [\.\- ]                                  # must have a separator (prevents s01e01-720p from being 720 episodes)
        [^\/]*$''',

        # foo.1x23-24*
        '''
        ^((?P<seriesname>.+?)[ \._\-])?          # show name
        (?P<seasonnumber>[0-9]+)                 # 1
        [xX](?P<episodenumberstart>[0-9]+)       # first x23
        (                                        # -24 etc
             [\-][0-9]+
        )*
             [\-]                                # separator
             (?P<episodenumberend>[0-9]+)        # final episode num
        ([\.\- ].*                               # must have a separator (prevents 1x01-720p from being 720 episodes)
        |
        $)''',

        # foo.[1x09-11]*
        '''^(?P<seriesname>.+?)[ \._\-]          # show name and padding
        \[                                       # [
            ?(?P<seasonnumber>[0-9]+)            # season
        [xX]                                     # x
            (?P<episodenumberstart>[0-9]+)       # episode
            (- [0-9]+)*
        -                                        # -
            (?P<episodenumberend>[0-9]+)         # episode
        \]                                       # \]
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\\/]*$''',

        # foo.s0101, foo.0201
        '''^(?P<seriesname>.+?)[ \._\-]
        [Ss](?P<seasonnumber>[0-9]{2})
        [\.\- ]?
        (?P<episodenumber>[0-9]{2})
        [^0-9]*$''',

        # foo.1x09*
        '''^((?P<seriesname>.+?)[ \._\-])?       # show name and padding
        \[?                                      # [ optional
        (?P<seasonnumber>[0-9]+)                 # season
        [xX]                                     # x
        (?P<episodenumber>[0-9]+)                # episode
        \]?                                      # ] optional
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\\/]*$''',

        # foo.s01.e01, foo.s01_e01
        '''^((?P<seriesname>.+?)[ \._\-])?
        [Ss](?P<seasonnumber>[0-9]+)[\.\- ]?
        [Ee](?P<episodenumber>[0-9]+)[\.\- ]+
        ((?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\\/]*?$''',

        # foo.2010.01.02.etc
        '''
        ^((?P<seriesname>.+?)[ \._\-])?         # show name
        (?P<year>\d{4})                          # year
        [ \._\-]                                 # separator
        (?P<month>\d{2})                         # month
        [ \._\-]                                 # separator
        (?P<day>\d{2})                           # day
        ([\.\- ]+(?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # Foo - S2 E 02 - etc
        '''^(?P<seriesname>.+?)[ ]?[ \._\-][ ]?
        [Ss](?P<seasonnumber>[0-9]+)[\.\- ]?
        [Ee][ ]?(?P<episodenumber>[0-9]+)
        [^\\/]*$''',

        # scene.name.s02.etc (whole season, episode = empty list)
        '''^((?P<seriesname>.+?)[ \._])?
        [Ss](?P<seasonnumberonly>[0-9]+)[\.\_ ]+?
        ((?P<episodename>.+?)(\.(?P<ext>\w{3,4}))?$)?           # get the episode name & extension if it is available
        [^\/]*$''',

        # Show - Episode 9999 [S 12 - Ep 131] - etc
        '''
        (?P<seriesname>.+)                       # Showname
        [ ]-[ ]                                  # -
        [Ee]pisode[ ]\d+                         # Episode 1234 (ignored)
        [ ]
        \[                                       # [
        [sS][ ]?(?P<seasonnumber>\d+)            # s 12
        ([ ]|[ ]-[ ]|-)                          # space, or -
        ([eE]|[eE]p)[ ]?(?P<episodenumber>\d+)   # e or ep 12
        \]                                       # ]
        .*$                                      # rest of file
        ''',

        # show.name.e123.abc
        '''^(?P<seriesname>.+?)                  # Show name
        [ \._\-]                                 # Padding
        (?P<episodenumber>[0-9]+)                # 2
        of                                       # of
        [ \._\-]?                                # Padding
        \d+                                      # 6
        ([\._ -]|$|[^\\/]*$)                     # More padding, then anything
        ''',

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
        '''^(?P<seriesname>.+?)                  # Show name
        [ \._\-]                                 # Padding
        [Ee](?P<episodenumber>[0-9]+)            # E123
        [\._ -][^\\/]*$                          # More padding, then anything
        ''',

        # Show name Part 1
        '''^(?P<seriesname>.+?)                              # Show name
        [ \._\-]                                             # Padding
        [Pp][Aa]?[Rr]?[Tt][\._ -]?(?P<episodenumber>[0-9]+)  # Part 1 
        [\._ -][^\\/]*$                                      # More padding, then anything
        ''',

        # match stupid scene names like tpz-abc123.avi
        '''
        ^(?:[A-Za-z]{3,})\-(?P<seriesname>\w+?)  # get series name (even though it's probably a meaningless acronym)
        (?P<seasonnumber>\d{1,2})                # season number is either the first one or two digits
        (?P<episodenumber>\d\d)                  # ep number is always the last 2 digits
        \.\w+$                                   # dirnames should never be this stupid so require an extension
        ''',

        # Show.Name.Part.1
        '''^(?i)
        (?P<seriesname>.+?)                      # Show name
        [ \._\-]                                 # Padding
        (?:part|pt)[\._ -]?
        (?P<episodenumber>[0-9]+|[ivx]+)         # Part 1 
        [\._ -][^\\/]*$                          # More padding, then anything
        ''',
        
    ],

    # Formats for renamed files. Variations for with/without episode,
    # and with/without season number.
    'filename_with_episode':
     '%(seriesname)s - [%(seasonno)02dx%(episode)s] - %(episodename)s%(ext)s',
    'filename_season_only_with_episode':
     '%(seriesname)s - [S%(seasonno)02d] - %(episodename)s%(ext)s',
    'filename_without_episode':
     '%(seriesname)s - [%(seasonno)02dx%(episode)s]%(ext)s',
    'filename_season_only_without_episode':
     '%(seriesname)s - [S%(seasonno)02d]%(ext)s',
     'filename_with_episode_no_season':
      '%(seriesname)s - [%(episode)s] - %(episodename)s%(ext)s',
     'filename_without_episode_no_season':
      '%(seriesname)s - [%(episode)s]%(ext)s',

    # Used to join multiple episode names together
    'multiep_join_name_with': ', ',

    # Format for numbers (python string format), %02d does 2-digit
    # padding, %d will cause no padding
    'episode_single': '%02d',

    # String to join multiple number
    'episode_separator': '-',
}
