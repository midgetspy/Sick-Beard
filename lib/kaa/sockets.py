# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# sockets.py - TCP/Unix Socket for the Kaa Framework
# -----------------------------------------------------------------------------
# $Id: sockets.py 4070 2009-05-25 15:32:31Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2005-2009 Dirk Meyer, Jason Tackaberry, et al.
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = [ 'Socket', 'SocketError' ]

import sys
import errno
import os
import socket
import logging

from thread import threaded
from io import IO_READ, IO_WRITE, IOChannel
from utils import property, tempfile

# get logging object
log = logging.getLogger('base')

class SocketError(Exception):
    pass

class Socket(IOChannel):
    """
    Communicate over TCP or Unix sockets, implementing fully asynchronous reads
    and writes.
    """
    __kaasignals__ = {
        'new-client':
            '''
            Emitted when a new client connects to a listening socket.

            ``def callback(client, ...)``

            :param client: the new client that just connected.
            :type client: :class:`~kaa.Socket` object
            '''
    }

    def __init__(self, buffer_size=None, chunk_size=1024*1024):
        self._connecting = False
        self._addr = None
        self._listening = False
        self._buffer_size = buffer_size

        super(Socket, self).__init__(chunk_size=chunk_size)


    @IOChannel.fileno.getter
    def fileno(self):
        # If fileno() is accessed on a closed socket, socket.error is
        # railsed.  So we override our superclass's implementation to
        # handle this case.
        try:
            return self._channel.fileno()
        except (AttributeError, socket.error):
            return None


    @property
    def address(self):
        """
        Either a 2-tuple containing the (host, port) of the remote end of the
        socket, or a string in the case of a UNIX socket.

        host may be an IP address or hostname, but it is always a string.

        If this is a listening socket, it is a 2-tuple of the address
        the socket was bound to.
        """
        return self._addr


    @property
    def listening(self):
        """
        True if this is a listening socket, and False otherwise.
        """
        return self._listening


    @property
    def connecting(self):
        """
        True if the socket is in the process of establishing a connection
        but is not yet connected.
        
        Once the socket is connected, the connecting property will be False,
        but the connected property will be True.
        """
        return self._connecting


    @property
    def connected(self):
        """
        Boolean representing the connected state of the socket.
        """
        try:
            # Will raise exception if socket is not connected.
            self._channel.getpeername()
            return True
        except (AttributeError, socket.error):
            # AttributeError is raised if _channel is None, socket.error is
            # raised if the socket is disconnected
            return False


    @property
    def alive(self):
        """
        True if the socket is alive, and False otherwise.

        A socket is considered alive when it is connected or in the process of
        connecting.
        """
        return self.connected or self.connecting


    @IOChannel.readable.getter
    def readable(self):
        """
        True if the socket is readable, and False otherwise.
        
        A socket is considered readable when it is listening or alive.
        """
        # Note: this property is used in superclass's _update_read_monitor()
        return self._listening or self.alive


    @property
    def buffer_size(self):
        """
        Size of the send and receive socket buffers (SO_SNDBUF and SO_RCVBUF)
        in bytes.
        
        Setting this to higher values (say 1M) improves performance when
        sending large amounts of data across the socket.  Note that the upper
        bound may be restricted by the kernel.  (Under Linux, this can be tuned
        by adjusting /proc/sys/net/core/[rw]mem_max)
        """
        return self._buffer_size


    @buffer_size.setter
    def buffer_size(self, size):
        self._buffer_size = size
        if self._channel and size:
            self._set_buffer_size(self._channel, size)


    def _set_buffer_size(self, s, size):
        """
        Sets the send and receive buffers of the given socket s to size.
        """
        s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, size)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, size)


    def _normalize_address(self, addr):
        """
        Converts address strings in the form host:port into 2-tuples containing
        the hostname and integer port.  Strings not in that form are assumed to
        represent unix socket paths.  If such a string does not start with /, a
        tempfile is used using kaa.tempfile().  If we can't make sense of the
        given address, a ValueError exception will be raised.
        """
        if isinstance(addr, basestring):
            if addr.count(':') == 1:
                addr, port = addr.split(':')
                if not port.isdigit():
                    raise ValueError('Port specified is not an integer')
                return addr, int(port)
            elif not addr.startswith('/'):
                return tempfile(addr)
        elif not isinstance(addr, (tuple, list)) or len(addr) != 2:
            raise ValueError('Invalid address')

        return addr


    def _make_socket(self, addr=None, overwrite=False):
        """
        Constructs a socket based on the given addr.  Returns the socket and
        the normalized address as a 2-tuple.

        If overwrite is True, if addr specifies a path to a unix socket and
        that unix socket already exists, it will be removed if the socket is
        not actually in use.  If it is in use, an IOError will be raised.
        """
        addr = self._normalize_address(addr)
        assert(type(addr) in (str, tuple, None))

        if isinstance(addr, basestring):
            if overwrite and os.path.exists(addr):
                # Unix socket exists; test to see if it's active.
                try:
                    dummy = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    dummy.connect(addr)
                except socket.error, (err, msg):
                    if err == errno.ECONNREFUSED:
                        # Socket is not active, so we can remove it.
                        log.debug('Replacing dead unix socket at %s' % addr)
                    else:
                        # Reraise unexpected exception
                        tp, exc, tb = sys.exc_info()
                        raise tp, exc, tb
                else:
                    # We were able to connect to the existing socket, so it's
                    # in use.  We won't overwrite it.
                    raise IOError('Address already in use')
                os.unlink(addr)

            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        return sock, addr


    def listen(self, bind_info, qlen=5):
        """
        Sets the socket to listen.

        :param bind_info: Binds the socket using this value.  If an int, this
                          specifies a port that is bound on all interfaces; if
                          a 2-tuple, specifies (ip, port) where ip is the
                          single interface on which to bind.
        :type bind_info: int or 2-tuple

        If the bind fails, an exception is raised.

        Once listening, new connections are automatically accepted, and
        the 'new-client' signal is emitted for each new connection.  Callbacks
        connecting to the signal will receive a new Socket object representing
        the client connection.
        """
        if isinstance(bind_info, int):
            # Only port number specified; translate to tuple that can be
            # used with socket.bind()
            bind_info = ('', bind_info)

        sock, addr = self._make_socket(bind_info, overwrite=True)
        sock.bind(addr)
        if addr[1] == 0:
            # get real port used
            addr = (addr[0], sock.getsockname()[1])
        sock.listen(qlen)
        self._listening = True
        self.wrap(sock, addr)


    @threaded()
    def _connect(self, addr):
        sock, addr = self._make_socket(addr)
        try:
            if type(addr) == str:
                # Unix socket, just connect.
                sock.connect(addr)
            else:
                host, port = addr
                if not host.replace(".", "").isdigit():
                    # Resolve the hostname.
                    host = socket.gethostbyname(host)
                sock.connect((host, port))
        finally:
            self._connecting = False

        self.wrap(sock, addr)


    def connect(self, addr):
        """
        Connects to the host specified in address.

        :param addr: if a string in the form host:port, or a tuple 
                     the form (host, port), a TCP socket is established.
                     Otherwise a Unix socket is established and addr is treated
                     as a filename.  In this case, if addr does not start with
                     a / character, a kaa tempfile is created.
        :type addr: str or 2-tuple

        :returns: An :class:`~kaa.InProgress` object.

        This function is executed in a thread to avoid blocking.  It therefore
        returns an InProgress object.  If the socket is connected, the InProgress
        is finished with no arguments.  If the connection cannot be established,
        an exception is thrown to the InProgress.
        """
        self._connecting = True
        return self._connect(addr)


    def wrap(self, sock, addr=None):
        """
        Wraps an existing low-level socket object.
        
        addr specifies the address corresponding to the socket.
        """
        super(Socket, self).wrap(sock, IO_READ|IO_WRITE)
        self._addr = addr or self._addr

        if self._buffer_size:
            self._set_buffer_size(sock, self._buffer_size)


    def _is_read_connected(self):
        return self._listening or super(Socket, self)._is_read_connected()


    def _set_non_blocking(self):
        self._channel.setblocking(False)


    def _read(self, size):
        return self._channel.recv(size)


    def _write(self, data):
        return self._channel.send(data)


    def _accept(self):
        """
        Accept a new connection and return a new Socket object.
        """
        sock, addr = self._channel.accept()
        # create new Socket from the same class this object is
        client_socket = self.__class__()
        client_socket.wrap(sock, addr)
        self.signals['new-client'].emit(client_socket)


    def _handle_read(self):
        if self._listening:
            return self._accept()

        return super(Socket, self)._handle_read()


    def close(self, immediate=False, expected=True):
        """
        Closes the socket.
        
        :param immediate: if False and there is data in the write buffer, the
                          channel is closed once the write buffer is emptied.
                          Otherwise the channel is closed immediately and the 
                          *closed* signal is emitted.
        :type immediate: bool
        """
        super(Socket, self).close(immediate, expected)
        if self._listening and isinstance(self._addr, basestring) and self._addr.startswith('/'):
            # Remove unix socket if it exists.
            try:
                os.unlink(self._addr)
            except OSError:
                pass

        self._addr = None
