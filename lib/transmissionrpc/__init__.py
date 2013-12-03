# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT, PRIORITY, RATIO_LIMIT, LOGGER
from transmissionrpc.error import TransmissionError, HTTPHandlerError
from transmissionrpc.httphandler import HTTPHandler, DefaultHTTPHandler
from transmissionrpc.torrent import Torrent
from transmissionrpc.session import Session
from transmissionrpc.client import Client
from transmissionrpc.utils import add_stdout_logger, add_file_logger

__author__    		= 'Erik Svensson <erik.public@gmail.com>'
__version_major__   = 0
__version_minor__   = 12
__version__   		= '{0}.{1}'.format(__version_major__, __version_minor__)
__copyright__ 		= 'Copyright (c) 2008-2013 Erik Svensson'
__license__   		= 'MIT'
