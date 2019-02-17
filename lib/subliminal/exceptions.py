# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class Error(Exception):
    """Base class for exceptions in subliminal"""


class ProviderError(Error):
    """Exception raised by providers"""


class ConfigurationError(ProviderError):
    """Exception raised by providers when badly configured"""


class AuthenticationError(ProviderError):
    """Exception raised by providers when authentication failed"""


class DownloadLimitExceeded(ProviderError):
    """Exception raised by providers when download limit is exceeded"""
