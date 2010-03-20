#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvnamer
#repository:http://github.com/dbr/tvnamer
#license:Creative Commons GNU GPL v2
# http://creativecommons.org/licenses/GPL/2.0/

"""Exceptions used through-out tvnamer
"""


class BaseTvnamerException(Exception):
    """Base exception all tvnamers exceptions inherit from
    """
    pass


class InvalidPath(BaseTvnamerException):
    """Raised when an argument is a non-existent file or directory path
    """
    pass


class NoValidFilesFoundError(BaseTvnamerException):
    """Raised when no valid files are found. Effectively exits tvnamer
    """
    pass


class InvalidFilename(BaseTvnamerException):
    """Raised when a file is parsed, but no episode info can be found
    """
    pass


class UserAbort(BaseTvnamerException):
    """Base exception for config errors
    """
    pass


class BaseConfigError(BaseTvnamerException):
    """Base exception for config errors
    """
    pass


class ConfigValueError(BaseConfigError):
    """Raised if the config file is malformed or unreadable
    """
    pass


class DataRetrievalError(BaseTvnamerException):
    """Raised when an error (such as a network problem) prevents tvnamer
    from being able to retrieve data such as episode name
    """


class ShowNotFound(DataRetrievalError):
    """Raised when a show cannot be found
    """
    pass


class SeasonNotFound(DataRetrievalError):
    """Raised when requested season cannot be found
    """
    pass


class EpisodeNotFound(DataRetrievalError):
    """Raised when episode cannot be found
    """
    pass


class EpisodeNameNotFound(DataRetrievalError):
    """Raised when the name of the episode cannot be found
    """
    pass
