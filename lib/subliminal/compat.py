# -*- coding: utf-8 -*-
import sys
import socket


if sys.version_info[0] == 2:
    from xmlrpclib import ServerProxy, Transport
    from httplib import HTTPConnection
elif sys.version_info[0] == 3:
    from xmlrpc.client import ServerProxy, Transport
    from http.client import HTTPConnection


class TimeoutTransport(Transport, object):
    def __init__(self, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, *args, **kwargs):
        super(TimeoutTransport, self).__init__(*args, **kwargs)
        self.timeout = timeout

    def make_connection(self, host):
        h = HTTPConnection(host, timeout=self.timeout)
        return h
