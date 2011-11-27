# -*- coding: utf-8 -*-

"""
requests.defaults
~~~~~~~~~~~~~~~~~

This module provides the Requests configuration defaults.

Configurations:

:base_headers: Default HTTP headers.
:verbose: Stream to write request logging to.
:timeout: Seconds until request timeout.
:max_redirects: Maximum njumber of redirects allowed within a request.
:decode_unicode: Decode unicode responses automatically?
:keep_alive: Reuse HTTP Connections?
:max_retries: The number of times a request should be retried in the event of a connection failure.
:safe_mode: If true, Requests will catch all errors.
:pool_maxsize: The maximium size of an HTTP connection pool.
:pool_connections: The number of active HTTP connection pools to use.

"""

from . import __version__

defaults = dict()


defaults['base_headers'] = {
    'User-Agent': 'python-requests/%s' % __version__,
    'Accept-Encoding': ', '.join(('identity', 'deflate', 'compress', 'gzip')),
    'Accept': '*/*'
}

defaults['verbose'] = None
defaults['max_redirects'] = 30
defaults['decode_unicode'] = True
defaults['pool_connections'] = 10
defaults['pool_maxsize'] = 10
defaults['max_retries'] = 0
defaults['safe_mode'] = False
defaults['keep_alive'] = True
