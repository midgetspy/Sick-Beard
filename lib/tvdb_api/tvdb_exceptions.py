#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)

"""Custom exceptions used or raised by tvdb_api
"""

__author__ = "dbr/Ben"
__version__ = "1.1"

__all__ = ["tvdb_error", "tvdb_userabort", "tvdb_shownotfound",
"tvdb_seasonnotfound", "tvdb_episodenotfound", "tvdb_attributenotfound"]

class tvdb_error(Exception):
    """An error with www.thetvdb.com (Cannot connect, for example)
    """
    pass

class tvdb_userabort(Exception):
    """User aborted the interactive selection (via
    the q command, ^c etc)
    """
    pass

class tvdb_shownotfound(Exception):
    """Show cannot be found on www.thetvdb.com (non-existant show)
    """
    pass

class tvdb_seasonnotfound(Exception):
    """Season cannot be found on www.thetvdb.com
    """
    pass

class tvdb_episodenotfound(Exception):
    """Episode cannot be found on www.thetvdb.com
    """
    pass

class tvdb_attributenotfound(Exception):
    """Raised if an episode does not have the requested
    attribute (such as a episode name)
    """
    pass
