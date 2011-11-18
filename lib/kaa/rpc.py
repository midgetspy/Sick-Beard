# -* -coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# rpc.py - Simple interprocess communication via remote procedure calls.
# -----------------------------------------------------------------------------
# $Id: rpc.py 4070 2009-05-25 15:32:31Z tack $
#
# This module defines an alternative way for InterProcessCommunication with
# less features than the ipc.py module. It does not keep references, return
# values are only given back as a callback and it is only possible to access
# functions.
#
# So wy use this module and not kaa.ipc? Well, kaa.ipc makes it very easy to
# shoot yourself into the foot. It keeps references over ipc which could
# confuse the garbage collector and a simple function call on an object can
# result in many mainloop steps incl. recursion inside the mainloop.
#
# *****************************************************************************
# API changes compared to kaa.rpc:
# *****************************************************************************
#
# 1. Channel.connect is renamed to Channel.register
#
# 2. authenticated signal is renamed to open
#
# 3. is_connected is removed
#
# 4. connected property is not True before authenticated
#
# 5. kaa.rpc.Channel() will not raise and exception on connection refused.
#    Use kaa.inprogress(client) to monitor the connection
#
# 6. New client argument: retry. If set to seconds, the client will
#    retry connecting and reconnects after close.
#
# 7. Please use kaa.rpc.connect instead of kaa.rpc.Client
#
# *****************************************************************************
#
# Documentation:
#
# Start a server: kaa.rpc.Server(address, secret)
# Start a client: kaa.rpc.Client(address, secret)
#
# Since everything is async, the challenge response is done in the background
# and you can start using it right away. If the authentication is wrong, it
# will fail without notifing the user (I know this is bad, but it is designed
# to work internaly where everything is correct).
#
# Next you need to define functions the remote side is allowed to call and
# give it a name. Use use expose for that.
#
# | class MyClass(object)
# |   @kaa.rpc.expose("do_something")
# |   def my_function(self, foo)
#
# Connect the object with that function to the server/client. You can connect
# as many objects as you want
# | server.connect(MyClass())
#
# The client can now call do_something (not my_function, this is the internal
# name). To do that, you need to create a RPC object with the callback you
# want to have
#
# | x = client.rpc('do_something', 6) or
# | x = client.rpc('do_something', foo=4)
#
# The result is an InProgress object. Connect to it to get the result.
#
# When a new client connects to the server, the 'client-connected' signals will
# be emitted with a Channel object as parameter. This object can be used to
# call functions on client side the same way the client calls functions on
# server side. The client and the channel objects have a signal 'disconnected'
# to be called when the connection gets lost.
#
# -----------------------------------------------------------------------------
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry
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

__all__ = [ 'Server', 'Client', 'expose' ]

# python imports
import types
import socket
import logging
import cPickle
import pickle
import struct
import sys
import sha
import time
import traceback

# kaa imports
import kaa
from main import is_shutting_down
from async import make_exception_class, AsyncExceptionBase
from utils import property
from object import Object

# get logging object
log = logging.getLogger('rpc')

# Global constants
RPC_PACKET_HEADER_SIZE = struct.calcsize("I4sI")


class RemoteException(AsyncExceptionBase):
    """
    Raised when remote RPC calls raise exceptions.  Instances of this class
    inherit the actual remote exception class, so this works:

        try:
            yield client.rpc('write_file')
        except IOError, (errno, msg):
            ...

    When RemoteException instances are printed, they will also include the
    traceback of the remote stack.
    """
    __metaclass__ = make_exception_class
    def _kaa_get_header(self):
        return "Exception during RPC call '%s'; remote traceback follows:" % self._kaa_exc_args[0]


class Server(Object):
    """
    RPC server class.  RPC servers accept incoming connections from client,
    however RPC calls can be issued in either direction.

    address specifies what address to bind the socket to, and can be in
    the form ip:port or hostname:port or as a 2-tuple (hostname, port).
    If hostname is an empty string, the socket is bound to all interfaces.
    If address is a string but not in the above form, it is assumed to be
    a unix socket.  See :meth:`kaa.Socket.connect` for more info.

    See kaa.Socket.buffer_size docstring for information on buffer_size.
    """
    __kaasignals__ = {
        'client-connected':
            '''
            Emitted when a new RPC client connects to this RPC server.

            .. describe:: def callback(client, ...)

               :param client: the new client that just connected
               :type client: :class:`~kaa.rpc.Client` object

            '''
    }
    def __init__(self, address, auth_secret = '', buffer_size=None):
        super(Server, self).__init__()
        self._auth_secret = auth_secret
        self._socket = kaa.Socket(buffer_size=buffer_size)
        self._socket.listen(address)
        self._socket.signals['new-client'].connect_weak(self._new_connection)

        self.objects = []

    def _new_connection(self, client_sock):
        """
        Callback when a new client connects.
        """
        log.debug("New connection %s", client_sock)
        client_sock.buffer_size = self._socket.buffer_size
        client = Channel(sock = client_sock, auth_secret = self._auth_secret)
        for obj in self.objects:
            client.register(obj)
        client._send_auth_challenge()
        kaa.inprogress(client).connect(self.signals['client-connected'].emit)


    def close(self):
        """
        Close the server socket.
        """
        self._socket.close()
        self._socket = None

    def register(self, obj):
        """
        Registers one or more previously exposed callables to any clients
        connecting to this RPC Server.

        :param obj: callable(s) to be accessible to connected clients.
        :type obj: callable, module, or class instance

        If a module is given, all exposed callables.
        """
        self.objects.append(obj)


    def disconnect(self, obj):
        """
        Disconnects a previously connected object.
        """
        try:
            self.objects.remove(obj)
        except ValueError:
            pass


class Channel(Object):
    """
    Channel object for two point communication, implementing the kaa.rpc
    protocol. The server creates a Channel object for each incoming client
    connection.  Client itself is also a Channel.
    """
    __kaasignals__ = {
        'closed':
            '''
            Emitted when the RPC channel is closed.

            .. describe:: def callback(...)
            ''',

        'open':
            '''
            Emitted when the RPC channel has successfully authenticated.

            .. describe:: def callback(...)
            '''
    }

    channel_type = 'server'

    def __init__(self, sock, auth_secret):
        super(Channel, self).__init__()
        self._socket = sock
        self._authenticated = False
        self._connect_inprogress = kaa.InProgress()
        # We start off in an unauthenticated state; set chunk size to something
        # small to prevent untrusted remote from flooding read buffer.
        self._socket.chunk_size = 1024
        # Buffer containing packets deferred until after authentication.
        self._write_buffer_deferred = []
        self._read_buffer = []
        self._callbacks = {}
        self._next_seq = 1
        self._rpc_in_progress = {}
        self._auth_secret = auth_secret
        self._pending_challenge = None

        # Creates a circular reference so that RPC channels survive even when
        # there is no reference to them.  (Servers may not hold references to
        # clients channels.)  As long as the socket is connected, the channel
        # will survive.
        self._socket.signals['read'].connect(self._handle_read)
        self._socket.signals['closed'].connect(self._handle_close)


    @property
    def connected(self):
        return self._socket.connected and self._connect_inprogress.finished


    def register(self, obj):
        """
        Registers one or more previously exposed callables to the peer

        :param obj: callable(s) to be accessible to.
        :type obj: callable, module, or class instance

        If a module is given, all exposed callables.
        """
        if type(obj) == types.FunctionType:
            callables = [obj]
        elif type(obj) == types.ModuleType:
            callables = [ getattr(obj, func) for func in dir(obj) if not func.startswith('_')]
        else:
            callables = [ getattr(obj, func) for func in dir(obj) ]

        for func in callables:
            if callable(func) and hasattr(func, '_kaa_rpc'):
                self._callbacks[func._kaa_rpc] = func


    def rpc(self, cmd, *args, **kwargs):
        """
        Call the remote command and return InProgress.
        """
        if not kaa.is_mainthread():
            # create InProgress object and return
            callback = kaa.InProgress()
            kwargs['_kaa_rpc_callback'] = callback
            kaa.MainThreadCallback(self.rpc)(cmd, *args, **kwargs)
            return callback
        seq = self._next_seq
        self._next_seq += 1
        # create InProgress object
        callback = kwargs.pop('_kaa_rpc_callback', kaa.InProgress())
        packet_type = 'CALL'
        payload = cPickle.dumps((cmd, args, kwargs), pickle.HIGHEST_PROTOCOL)
        self._send_packet(seq, packet_type, payload)
        # callback with error handler
        self._rpc_in_progress[seq] = (callback, cmd)
        return callback


    def close(self):
        """
        Forcefully close the RPC channel.
        """
        self._socket.close()


    def __inprogress__(self):
        return self._connect_inprogress


    def _write(self, data):
        """
        Writes data to the channel.
        """
        cb = kaa.WeakCallback(self._handle_close, False)
        cb.ignore_caller_args = True
        self._socket.write(data).exception.connect(cb)


    def _handle_close(self, expected, reset_signals=True):
        """
        kaa.Socket callback invoked when socket is closed.
        """
        if not self._socket or not self._socket.alive:
            # Socket already closed.  Return False to indicate the exception
            # was handled, if invoked from write() exception handler.
            return False

        if not self._authenticated:
            # Socket closed before authentication completed.  We assume it's
            # because authentication failed (though it may not be).
            log.error('Socket closed before authentication completed')

        log.debug('close socket for %s', self)
        self.signals['closed'].emit()
        if reset_signals:
            self.signals = {}
        self._socket.signals['read'].disconnect(self._handle_read)
        self._socket.signals['closed'].disconnect(self._handle_close)
        while self._rpc_in_progress:
            # raise exception for callback
            callback = self._rpc_in_progress.popitem()[1][0]
            if callback and (not is_shutting_down() or callback.count() or callback.exception.count()):
                # Raise an error if this happens during runtime or if
                # someone wants to get the result or exception.
                callback.throw(IOError, IOError('kaa.rpc channel closed'), None)

        # Return False for reason explained above.
        return False


    def _handle_read(self, data):
        """
        Invoked when a new chunk is read from the socket.  When not authenticated,
        chunk size is 1k; when authenticated it is 1M.
        """
        self._read_buffer.append(data)
        # Before we start into the loop, make sure we have enough data for
        # a full packet.  For very large packets (if we just received a huge
        # pickled object), this saves the string.join() which can be very
        # expensive.  (This is the reason we use a list for our read buffer.)
        buflen = sum(len(x) for x in self._read_buffer)
        if buflen < RPC_PACKET_HEADER_SIZE:
            return

        if not self._authenticated and buflen > 1024:
            # Because we are not authenticated, we shouldn't have more than 1k
            # in the buffer.  If we do it's because the remote has sent a
            # large amount of data before completing authentication.
            log.warning("Too much data received from remote end before authentication; disconnecting")
            self.close()
            return

        # Ensure the first block in the read buffer is big enough for a full
        # packet header.  If it isn't, then we must have more than 1 block in
        # the buffer, so keep merging blocks until we have a block big enough
        # to be a header.  If we're here, it means that buflen >=
        # RPC_PACKET_HEADER_SIZE, so we can safely loop.
        while len(self._read_buffer[0]) < RPC_PACKET_HEADER_SIZE:
            self._read_buffer[0] += self._read_buffer.pop(1)

        # Make sure the the buffer holds enough data as indicated by the
        # payload size in the header.
        header = self._read_buffer[0][:RPC_PACKET_HEADER_SIZE]
        payload_len = struct.unpack("I4sI", header)[2]
        if buflen < payload_len + RPC_PACKET_HEADER_SIZE:
            return

        # At this point we know we have enough data in the buffer for the
        # packet, so we merge the array into a single buffer.
        strbuf = ''.join(self._read_buffer)
        self._read_buffer = []
        while True:
            if len(strbuf) <= RPC_PACKET_HEADER_SIZE:
                if len(strbuf) > 0:
                    self._read_buffer.append(str(strbuf))
                break
            header = strbuf[:RPC_PACKET_HEADER_SIZE]
            seq, packet_type, payload_len = struct.unpack("I4sI", header)
            if len(strbuf) < payload_len + RPC_PACKET_HEADER_SIZE:
                # We've also received portion of another packet that we
                # haven't fully received yet.  Put back to the buffer what
                # we have so far, and we can exit the loop.
                self._read_buffer.append(str(strbuf))
                break

            # Grab the payload for this packet, and shuffle strbuf to the
            # next packet.
            payload = strbuf[RPC_PACKET_HEADER_SIZE:RPC_PACKET_HEADER_SIZE + payload_len]
            strbuf = buffer(strbuf, RPC_PACKET_HEADER_SIZE + payload_len)
            #log.debug("Got packet %s", packet_type)
            if not self._authenticated:
                self._handle_packet_before_auth(seq, packet_type, payload)
            else:
                self._handle_packet_after_auth(seq, packet_type, payload)


    def _send_packet(self, seq, packet_type, payload):
        """
        Send a packet (header + payload) to the other side.
        """
        if not self._socket:
            return
        header = struct.pack("I4sI", seq, packet_type, len(payload))
        if not self._authenticated and packet_type not in ('RESP', 'AUTH'):
            log.debug('delay packet %s', packet_type)
            self._write_buffer_deferred.append(header + payload)
        else:
            self._write(header + payload)


    def _send_answer(self, answer, seq):
        """
        Send delayed answer when callback returns InProgress.
        """
        payload = cPickle.dumps(answer, pickle.HIGHEST_PROTOCOL)
        self._send_packet(seq, 'RETN', payload)


    def _send_exception(self, type, value, tb, seq):
        """
        Send delayed exception when callback returns InProgress.
        """
        stack = traceback.extract_tb(tb)
        try:
            payload = cPickle.dumps((value, stack), pickle.HIGHEST_PROTOCOL)
        except cPickle.UnpickleableError:
            payload = cPickle.dumps((Exception(str(value)), stack), pickle.HIGHEST_PROTOCOL)
        self._send_packet(seq, 'EXCP', payload)


    def _handle_packet_after_auth(self, seq, type, payload):
        """
        Handle incoming packet (called from _handle_write) after
        authentication has been completed.
        """
        if type == 'CALL':
            # Remote function call, send answer
            function, args, kwargs = cPickle.loads(payload)
            try:
                if self._callbacks[function]._kaa_rpc_param[0]:
                    args = [ self ] + list(args)
                result = self._callbacks[function](*args, **kwargs)
            except Exception, e:
                #log.exception('Exception in rpc function "%s"', function)
                if not function in self._callbacks:
                    log.error('%s - %s', function, self._callbacks.keys())
                self._send_exception(*sys.exc_info() + (seq,))
                return True

            if isinstance(result, kaa.InProgress):
                result.connect(self._send_answer, seq)
                result.exception.connect(self._send_exception, seq)
            else:
                self._send_answer(result, seq)

            return True

        if type == 'RETN':
            # RPC return
            payload = cPickle.loads(payload)
            callback, cmd = self._rpc_in_progress.get(seq)
            if callback is None:
                return True
            del self._rpc_in_progress[seq]
            callback.finish(payload)
            return True

        if type == 'EXCP':
            # Exception for remote call
            exc_value, stack = cPickle.loads(payload)
            callback, cmd = self._rpc_in_progress.get(seq)
            if callback is None:
                return True
            del self._rpc_in_progress[seq]
            remote_exc = RemoteException(exc_value, stack, cmd)
            callback.throw(remote_exc.__class__, remote_exc, None)
            return True

        log.error('unknown packet type %s', type)
        return True


    def _handle_packet_before_auth(self, seq, type, payload):
        """
        This function handles any packet received by the remote end while we
        are waiting for authentication.  It responds to AUTH or RESP packets
        (auth packets) while closing the connection on all other packets (non-
        auth packets).

        Design goals of authentication:
           * prevent unauthenticated connections from executing RPC commands
             other than 'auth' commands.
           * prevent unauthenticated connections from causing denial-of-
             service at or above the RPC layer.
           * prevent third parties from learning the shared secret by
             eavesdropping the channel.

        Non-goals:
           * provide any level of security whatsoever subsequent to successful
             authentication.
           * detect in-transit tampering of authentication by third parties
             (and thus preventing successful authentication).

        The parameters 'seq' and 'type' are untainted and safe.  The parameter
        payload is potentially dangerous and this function must handle any
        possible malformed payload gracefully.

        Authentication is a 4 step process and once it has succeeded, both
        sides should be assured that they share the same authentication secret.
        It uses a challenge-response scheme similar to CRAM.  The party
        responding to a challenge will hash the response with a locally
        generated salt to prevent a Chosen Plaintext Attack.  (Although CPA is
        not very practical, as they require the client to connect to a rogue
        server.) The server initiates authentication.

           1. Server sends challenge to client (AUTH packet)
           2. Client receives challenge, computes response, generates a
              counter-challenge and sends both to the server in reply (RESP
              packet with non-null challenge).
           3. Server receives response to its challenge in step 1 and the
              counter-challenge from server in step 2.  Server validates
              client's response.  If it fails, server logs the error and
              disconnects.  If it succeeds, server sends response to client's
              counter-challenge (RESP packet with null challenge).  At this
              point server considers client authenticated and allows it to send
              non-auth packets.
           4. Client receives server's response and validates it.  If it fails,
              it disconnects immediately.  If it succeeds, it allows the server
              to send non-auth packets.

        Step 1 happens when a new connection is initiated.  Steps 2-4 happen in
        this function.  3 packets are sent in this handshake (steps 1-3).

        WARNING: once authentication succeeds, there is implicit full trust.
        There is no security after that point, and it should be assumed that
        the client can invoke arbitrary calls on the server, and vice versa,
        because no effort is made to validate the data on the channel.

        Also, individual packets aren't authenticated.  Once each side has
        sucessfully authenticated, this scheme cannot protect against
        hijacking or denial-of-service attacks.

        One goal is to restrict the code path taken packets sent by
        unauthenticated connections.  That path is:

           _handle_read() -> _handle_packet_before_auth()

        Therefore these functions must be able to handle malformed and/or
        potentially malicious data on the channel, and as a result they are
        highly paranoid.  When these methods calls other functions, it must do
        so only with untainted data.  Obviously one assumption is that the
        underlying python calls made in these methods (particularly
        struct.unpack) aren't susceptible to attack.
        """
        if type not in ('AUTH', 'RESP'):
            # Received a non-auth command while expecting auth.
            self._connect_inprogress.throw(IOError, IOError('got %s before authentication is complete; closing socket.' % type), None)
            # Hang up.
            self.close()
            return

        try:
            # Payload could safely be longer than 20+20+20 bytes, but if it
            # is, something isn't quite right.  We'll be paranoid and
            # disconnect unless it's exactly 60 bytes.
            assert(len(payload) == 60)

            # Unpack the auth packet payload into three separate 20 byte
            # strings: the challenge, response, and salt.  If challenge is
            # not NULL (i.e. '\x00' * 20) then the remote is expecting a
            # a response.  If response is not NULL then salt must also not
            # be NULL, and the salt is used along with the previously sent
            # challenge to validate the response.
            challenge, response, salt = struct.unpack("20s20s20s", payload)
        except (AssertionError, struct.error):
            self._connect_inprogress.throw(IOError, IOError('Malformed authentication packet from remote; disconnecting.'), None)
            self.close()
            return

        # At this point, challenge, response, and salt are 20 byte strings of
        # arbitrary binary data.  They're considered benign.

        if type == 'AUTH':
            # Step 2: We've received a challenge.  If we've already sent a
            # challenge (which is the case if _pending_challenge is not None),
            # then something isn't right.  This could be a DoS so we'll
            # disconnect immediately.
            if self._pending_challenge:
                self._pending_challenge = None
                self.close()
                return

            # Otherwise send the response, plus a challenge of our own.
            response, salt = self._get_challenge_response(challenge)
            self._pending_challenge = self._get_rand_value()
            payload = struct.pack("20s20s20s", self._pending_challenge, response, salt)
            self._send_packet(seq, 'RESP', payload)
            log.debug('Got initial challenge from server, sending response.')
            return

        elif type == 'RESP':
            # We've received a reply to an auth request.

            if self._pending_challenge == None:
                # We've received a response packet to auth, but we haven't
                # sent a challenge.  Something isn't right, so disconnect.
                self.close()
                return

            # Step 3/4: We are expecting a response to our previous challenge
            # (either the challenge from step 1, or the counter-challenge from
            # step 2).  First compute the response we expect to have received
            # based on the challenge sent earlier, our shared secret, and the
            # salt that was generated by the remote end.

            expected_response = self._get_challenge_response(self._pending_challenge, salt)[0]
            # We have our response, so clear the pending challenge.
            self._pending_challenge = None
            # Now check to see if we were sent what we expected.
            if response != expected_response:
                self._connect_inprogress.throw(IOError, IOError('authentication error.'), None)
                self.close()
                return

            # Challenge response was good, so the remote is considered
            # authenticated now.  We increase the chunk size on the socket
            # so we read more at once.
            self._authenticated = True
            self._socket.chunk_size = 1024*1024
            log.debug('Valid response received, remote authenticated.')

            # If remote has issued a counter-challenge along with their
            # response (step 2), we'll respond.  Unless something fishy is
            # going on, this should always succeed on the remote end, because
            # at this point our auth secrets must match.  A challenge is
            # considered issued if it is not NULL ('\x00' * 20).  If no
            # counter-challenge was received as expected from step 2, then
            # authentication is only one-sided (we trust the remote, but the
            # remote won't trust us).  In this case, things won't work
            # properly, but there are no negative security implications.
            if len(challenge.strip("\x00")) != 0:
                response, salt = self._get_challenge_response(challenge)
                payload = struct.pack("20s20s20s", '', response, salt)
                self._send_packet(seq, 'RESP', payload)
                log.debug('Sent response to challenge from client.')

            # Empty deferred write buffer now that we're authenticated.
            self._write(''.join(self._write_buffer_deferred))
            self._write_buffer_deferred = []
            self._handle_connected()


    def _handle_connected(self):
        """
        Callback when the channel is authenticated and ready to be used
        """
        self._connect_inprogress.finish(self)
        self.signals['open'].emit()


    def _get_rand_value(self):
        """
        Returns a 20 byte value which is computed as a SHA hash of the
        current time concatenated with 64 bytes from /dev/urandom.  This
        value is not by design a nonce, but in practice it probably is.
        """
        rbytes = file("/dev/urandom").read(64)
        return sha.sha(str(time.time()) + rbytes).digest()


    def _send_auth_challenge(self):
        """
        Send challenge to remote end to initiate authentication handshake.
        """
        self._pending_challenge = self._get_rand_value()
        payload = struct.pack("20s20s20s", self._pending_challenge, '', '')
        self._send_packet(0, 'AUTH', payload)


    def _get_challenge_response(self, challenge, salt = None):
        """
        Generate a response for the challenge based on the auth secret supplied
        to the constructor.  This essentially implements CRAM, as defined in
        RFC 2195, using SHA-1 as the hash function, however the challenge is
        concatenated with a locally generated 20 byte salt to form the key,
        and the resulting key is padded to the SHA-1 block size, as with HMAC.

        If salt is not None, it is the value generated by the remote end that
        was used in computing their response.  If it is None, a new 20-byte
        salt is generated and used in computing our response.
        """
        def xor(s, byte):
            # XORs each character in string s with byte.
            return ''.join([ chr(ord(x) ^ byte) for x in s ])

        def H(s):
            # Returns the 20 byte SHA-1 digest of string s.
            return sha.sha(s).digest()

        if not salt:
            salt = self._get_rand_value()

        # block size of SHA-1 is 512 bits (64 bytes)
        B = 64
        # Key is auth secret concatenated with salt
        K = self._auth_secret + salt
        if len(K) > B:
            # key is larger than B, so first hash.
            K = H(K)
        # Pad K to be of length B
        K = K + '\x00' * (B - len(K))

        return H(xor(K, 0x5c) + H(xor(K, 0x36) + challenge)), salt


    def __repr__(self):
        tp = self.channel_type
        if not self._socket:
            return '<kaa.rpc.Channel (%s) - disconnected>' % tp
        return '<kaa.rpc.Channel (%s) %s>' % (tp, self._socket.fileno)



DISCONNECTED = 'DISCONNECTED'
CONNECTING = 'CONNECTING'
CONNECTED = 'CONNECTED'


class Client(Channel):
    """
    RPC client to be connected to a server.
    """

    channel_type = 'client'

    def __init__(self, address, auth_secret = '', buffer_size = None, retry = None):
        super(Client, self).__init__(kaa.Socket(buffer_size), auth_secret)
        self._socket.connect(address).exception.connect(self._handle_refused)
        self.monitoring = False
        if retry is not None:
            self._monitor(address, buffer_size, retry)
            self.monitoring = True

    def _handle_connected(self):
        """
        Callback when the channel is authenticated and ready to be used
        """
        self.status = CONNECTED
        super(Client, self)._handle_connected()

    def _handle_refused(self, type, value, tb):
        self._socket.signals['read'].disconnect(self._handle_read)
        self._socket.signals['closed'].disconnect(self._handle_close)
        self._connect_inprogress.throw(type, value, tb)
        return False

    def _handle_close(self, expected, reset_signals=True):
        """
        kaa.Socket callback invoked when socket is closed.
        """
        super(Client, self)._handle_close(expected, not self.monitoring)

    @kaa.coroutine()
    def _monitor(self, address, buffer_size, retry):
        while True:
            try:
                self.status = CONNECTING
                yield kaa.inprogress(self)
                # Python 2.4 code
                # FIXME: remove all python 2.4 supporting code
                self._connect_inprogress.result
                self.status = CONNECTED
                # wait until the socket is closed
                yield self.signals.subset('closed').any()
            except Exception, e:
                # connection failed
                pass
            self._connect_inprogress = kaa.InProgress()
            self.status = DISCONNECTED
            # wait some time until we retry
            yield kaa.delay(retry)
            # reset variables
            self._authenticated = False
            self._pending_challenge = None
            self._read_buffer = []
            self.status = CONNECTING
            self._socket = kaa.Socket(buffer_size)
            self._socket.chunk_size = 1024
            self._socket.signals['read'].connect(self._handle_read)
            self._socket.signals['closed'].connect(self._handle_close)
            self._socket.connect(address).exception.connect(self._handle_refused)


# expose Client as connect
connect = Client


def expose(command=None, add_client=False, coroutine=False):
    """
    Decorator to expose a function. If add_client is True, the client
    object will be added to the command list as first argument.
    """
    def decorator(func):
        if coroutine:
            func = kaa.coroutine()(func)
        func._kaa_rpc = command or func.func_name
        func._kaa_rpc_param = ( add_client, )
        return func
    return decorator
