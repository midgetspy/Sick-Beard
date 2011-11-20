# -* -coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# tls.py - TLS support for the Kaa Framework based on tlslite
# -----------------------------------------------------------------------------
# $Id: tls.py 4070 2009-05-25 15:32:31Z tack $
#
# This module wraps TLS for client and server based on tlslite. See
# http://trevp.net/tlslite/docs/public/tlslite.TLSConnection.TLSConnection-class.html
# for more information about optional paramater.
#
# -----------------------------------------------------------------------------
# Copyright 2008-2009 Dirk Meyer, Jason Tackaberry
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

# python imports
import logging
import os

# kaa imports
import kaa

# TODO: this file is a bit kludgy.  If we settle on this API (namely separate
# classes for tlslite and m2crypto) we should split this into separate files.

# TODO: needs more doc.

try:
# import tlslite.api to overwrite TLSConnection
    import tlslite.api
    import tlslite.errors
    #: Error to raise in the checker
    TLSAuthenticationError = tlslite.errors.TLSAuthenticationError
    TLSConnection = tlslite.api.TLSConnection
except ImportError:
    tlslite = None
    TLSConnection = object  # XXX: kludge

try:
    import M2Crypto
    M2Crypto.threading.init()
    kaa.signals['shutdown'].connect(M2Crypto.threading.cleanup)
except ImportError:
    M2Crypto = None

if tlslite == M2Crypto == None:
    raise ImportError('No available TLS library found (tried tlslite and m2crypto)')

# get logging object
log = logging.getLogger('tls')

# Search these standard system locations for the CA bundle.
CA_SEARCH_PATH = (
    '/etc/pki/tls/certs/ca-bundle.crt',
    '/usr/share/ssl/certs/ca-bundle.crt',
    '/usr/local/share/ssl/certs/ca-bundle.crt',
    '/etc/ssl/certs/ca-certificates.crt'
)

class TLSSocketError(Exception):
    pass


class TLSSocketBase(kaa.Socket):
    # list of suuported TLS authentication mechanisms (subclass must override)
    supported_methods = []
    
    # Cached system-wide CA cert file (as detected), or None if none was found.
    _cafile = False

    __kaasignals__ = {
        'tls':
            '''
            Emitted when a TLS handshake has been successfully completed.
            '''
    }

    def __init__(self, cafile=None):
        super(TLSSocketBase, self).__init__()
        self._handshake = False
        self._pre_handshake_write_queue = []

        if cafile:
            self._cafile = cafile
        elif TLSSocketBase._cafile is False:
            self._cafile = None
            for path in CA_SEARCH_PATH:
                if os.path.exists(path):
                    cafile = path
                    break
            else:
                # Maybe locate(1) can help.
                # XXX: assumes this is fast.  Maybe this should be done async.
                path = os.popen('locate -l 1 ca-certificates.crt ca-bundle.crt 2>/dev/null').readline().strip()
                if os.path.exists(path):
                    cafile = path

            TLSSocketBase._cafile = self._cafile = cafile


    def _is_read_connected(self):
        """
        Returns True if we're interested in read events.
        """
        # During the handshake stage, we handle all reads internally (within
        # TLSConnection).  So if self._handshake is True, we return False here
        # to prevent the IOChannel from responding to reads and passing data
        # from the TLS handshake back to the user.  If it's False, we defer to
        # the default behaviour.
        return not self._handshake and super(TLSSocketBase, self)._is_read_connected()


    @kaa.coroutine()
    def _prepare_tls(self):
        """
        Prepare TLS handshake. Flush the data currently in the write buffer
        and return the TLS connection object
        """
        self._handshake = True
        # Store current write queue and create a new one
        self._pre_handshake_write_queue = self._write_queue
        self._write_queue = []
        if self._pre_handshake_write_queue:
            # flush pre handshake write data
            yield self._pre_handshake_write_queue[-1][1]

        self._rmon.unregister()


    def _handle_write(self):
        if self._handshake:
            # Before starting the TLS handshake we created a new write
            # queue. The data send before TLS was started
            # (_pre_handshake_write_queue) must be send, after that we
            # give control over the socket to the TLS layer. Data
            # written while doing the handshake is send after it.
            if not self._pre_handshake_write_queue:
                # No data to send before the handshake
                return
            try:
                # Switch queues and send pre handshake data
                queue = self._write_queue
                self._write_queue = self._pre_handshake_write_queue
                super(TLSSocketBase, self)._handle_write()
            finally:
                self._write_queue = queue
        else:
            # normal operation
            super(TLSSocketBase, self)._handle_write()

    def _tls_client(self, *args ,**kwargs):
        # Implemented by subclass.  Must return InProgress.
        raise NotImplementedError()

    def _tls_server(self, *args ,**kwargs):
        # Implemented by subclass.  Must return InProgress.
        raise NotImplementedError()

    @kaa.coroutine()
    def _starttls(self, mode, *args, **kwargs):
        if not self.connected:
            raise RuntimeError('Socket not connected')

        self._handshake = True
        try:
            yield self._prepare_tls()
            yield getattr(self, '_tls_' + mode)(*args, **kwargs)
            self.signals['tls'].emit()
        finally:
            self._update_read_monitor()
            self._handshake = False

    def starttls_client(self, *args, **kwargs):
        return self._starttls('client', *args, **kwargs)
        
    def starttls_server(self, *args, **kwargs):
        return self._starttls('server', *args, **kwargs)



class TLSKey(object):
    """
    Class to hold the public (and private) key together with the certification chain.
    This class can be used with TLSSocket as key.
    """
    def __init__(self, filename, private, *certs):
        self.private = tlslite.api.parsePEMKey(open(filename).read(), private=private)
        self.certificate = tlslite.api.X509()
        self.certificate.parse(open(filename).read())
        chain = []
        for cert in (filename, ) + certs:
            x509 = tlslite.api.X509()
            x509.parse(open(cert).read())
            chain.append(x509)
        self.certificate.chain = tlslite.api.X509CertChain(chain)


class TLSLiteConnection(TLSConnection):
    """
    This class wraps a socket and provides TLS handshaking and data transfer.
    It enhances the tlslite version of the class with the same name with
    kaa support.
    """
    @kaa.coroutine()
    def _iterate_handshake(self, handshake):
        """
        Iterate through the TLS handshake for asynchronous calls using
        kaa.IOMonitor and kaa.InProgressCallback.
        """
        try:
            while True:
                n = handshake.next()
                cb = kaa.InProgressCallback()
                disp = kaa.IOMonitor(cb)
                if n == 0:
                    disp.register(self.sock.fileno(), kaa.IO_READ)
                if n == 1:
                    disp.register(self.sock.fileno(), kaa.IO_WRITE)
                yield cb
                disp.unregister()
        except StopIteration:
            pass

    def handshakeClientCert(self, certChain=None, privateKey=None, session=None,
                            settings=None, checker=None):
        """
        Perform a certificate-based handshake in the role of client.
        """
        handshake = tlslite.api.TLSConnection.handshakeClientCert(
            self, certChain=certChain, privateKey=privateKey, session=session,
            settings=settings, checker=checker, async=True)
        return self._iterate_handshake(handshake)

    def handshakeClientSRP(self, username, password, session=None,
                           settings=None, checker=None):
        """
        Perform a SRP-based handshake in the role of client.
        """
        handshake = tlslite.api.TLSConnection.handshakeClientSRP(
            self, username=username, password=password, session=session,
            settings=settings, checker=checker, async=True)
        return self._iterate_handshake(handshake)

    def handshakeServer(self, sharedKeyDB=None, verifierDB=None, certChain=None,
                        privateKey=None, reqCert=None, sessionCache=None,
                        settings=None, checker=None):
        """
        Start a server handshake operation on the TLS connection.
        """
        handshake = tlslite.api.TLSConnection.handshakeServerAsync(
            self, sharedKeyDB, verifierDB, certChain, privateKey, reqCert,
            sessionCache, settings, checker)
        return self._iterate_handshake(handshake)


    def fileno(self):
        """
        Return socket descriptor. This makes this class feel like a normal
        socket to the IOMonitor.
        """
        return self.sock.fileno()


    def close(self):
        """
        Close the socket.
        """
        if not self.closed:
            # force socket close or this will block
            # on kaa shutdown.
            self.sock.close()
        return tlslite.api.TLSConnection.close(self)



class TLSLiteSocket(TLSSocketBase):
    # list of suuported TLS authentication mechanisms
    supported_methods = [ 'X.509', 'SRP' ]

    @kaa.coroutine()
    def _tls_client(self, session=None, key=None, srp=None, checker=None):
        """
        Start a certificate-based handshake in the role of a TLS client.
        Note: this function DOES NOT check the server key based on the
        key chain. Provide a checker callback to be called for verification.
        http://trevp.net/tlslite/docs/public/tlslite.Checker.Checker-class.html
        Every callable object can be used as checker.

        @param session: tlslite.Session object to resume
        @param key: TLSKey object for client authentication
        @param srp: username, password pair for SRP authentication
        @param checker: callback to check the credentials from the server
        """
        if not self._rmon:
            raise RuntimeError('Socket not connected')

        if session is None:
            session = tlslite.api.Session()

        # create TLS connection object and unregister the read monitor
        tlscon = TLSLiteConnection(self._channel)
        tlscon.ignoreAbruptClose = True
        if key:
            yield tlscon.handshakeClientCert(session=session, checker=checker,
                      privateKey=key.private, certChain=key.certificate.chain)
        elif srp:
            yield tlscon.handshakeClientSRP(session=session, checker=checker,
                      username=srp[0], password=srp[1])
        else:
            yield tlscon.handshakeClientCert(session=session, checker=checker)
        self._channel = tlscon


    @kaa.coroutine()
    def _tls_server(self, session=None, key=None, request_cert=False, srp=None, checker=None):
        """
        Start a certificate-based or SRP-based handshake in the role of a TLS server.
        Note: this function DOES NOT check the client key if requested,
        provide a checker callback to be called for verification.
        http://trevp.net/tlslite/docs/public/tlslite.Checker.Checker-class.html
        Every callable object can be used as checker.

        @param session: tlslite.Session object to resume
        @param key: TLSKey object for server authentication
        @param request_cert: Request client certificate
        @param srp: tlslite.VerifierDB for SRP authentication
        @param checker: callback to check the credentials from the server
        """
        # create TLS connection object and unregister the read monitor
        tlscon = TLSLiteConnection(self._channel)
        tlscon.ignoreAbruptClose = True
        kwargs = {}
        if key:
            kwargs['privateKey'] = key.private
            kwargs['certChain'] = key.certificate.chain
        if srp:
            kwargs['verifierDB'] = srp
        if request_cert:
            kwargs['reqCert'] = True
        yield tlscon.handshakeServer(checker=checker, **kwargs)
        self._channel = tlscon



class M2TLSSocket(TLSSocketBase):
    # list of suuported TLS authentication mechanisms
    supported_methods = [ 'X.509' ]

    def _write(self, data):
        result = super(M2TLSSocket, self)._write(data)
        if isinstance(self._channel, M2Crypto.SSL.Connection) and result == -1:
            # M2Crypto will return -1 for non-blocking writes when the channel is
            # currently being used for SSL protocol handshaking.  So, we raise 
            # Resource Temporarily Unavailable, which makes the IOChannel retry
            # the write again later.
            raise IOError(11, 'Resource temporarily unavailable')
        return result


    def _read(self, chunk):
        if not isinstance(self._channel, M2Crypto.SSL.Connection):
            return super(M2TLSSocket, self)._read(chunk)
        try:
            result = super(M2TLSSocket, self)._read(chunk)
        except M2Crypto.SSL.SSLError, e:
            if e.message == 'unexpected eof':
                # M2Crypto raises an exception on EOF.  Return the empty
                # string to cause IOChannel to consider the socket closed.
                return ''
            raise
        else:
            if result is None:
                # As with writes, M2Crypto will return None for non-blocking reads when the
                # channel is being used for SSL handshaking.
                raise IOError(11, 'Resource temporarily unavailable')
        return result


    def _make_context(self, **kwargs):
        ctx = M2Crypto.SSL.Context()

        if kwargs.get('verify'):
            if not self._cafile:
                # Verification was requested but on CA bundle found, therefore
                # impossible to verify.
                raise TLSSocketError('CA bundle not found but verification requested.')
            else:
                # Load CA bundle.
                ctx.load_verify_locations(self._cafile)

        if 'dh' in kwargs:
            ctx.set_tmp_dh(kwargs['dh'])

        if 'cert' in kwargs:
            ctx.load_cert_chain(kwargs['cert'], keyfile=kwargs.get('key'))

        ctx.set_options(M2Crypto.SSL.op_all | M2Crypto.SSL.op_no_sslv2)
        ctx.set_verify(M2Crypto.SSL.verify_none, 10)
        return ctx


    def _post_check(self, con, kwargs):
        if kwargs.get('verify'):
            if not con.verify_ok():
                raise TLSSocketError('Peer certificate is not signed by a known CA')

        self.peer_cert = con.get_peer_cert()
        if 'check' in kwargs or self.peer_cert:
            check = kwargs.get('check', (None, None))
            if check[0] is None:
                # Validate peer CN by default.
                host = self.address[0]
            elif check[0] is False:
                # User requested to disable CN verification.
                host = None
            else:
                # User override for peer CN.
                host = check[0]
            fingerprint = check[1] if len(check) > 1 else None
            M2Crypto.SSL.Checker.Checker(host, fingerprint)(self.peer_cert)


    @kaa.threaded()
    def _tls_client(self, **kwargs):
        """
        TODO: document me.

        Possible kwargs:
            cert: filename to pem cert for local side
            key: private key file (if None, assumes key is in cert)
            dh: filename for Diffie-Hellman parameters (only used for server)
            verify: if True, checks that the peer cert is signed by a known CA
            check: 2-tuple (host, fingerprint) to control further peer cert checks:
                   host: None: validate CN from host from connect();
                         False: don't do any CN checking
                         string: require CN match the string
                   fingerprint: peer cert digest must match fingerprint, or None not to check.
        """
        ctx = self._make_context(**kwargs)
        con = M2Crypto.SSL.Connection(ctx, self._channel)

        con.setblocking(True)
        con.setup_ssl()
        con.set_connect_state()
        con.connect_ssl()
        con.setblocking(False)

        self._post_check(con, kwargs)
        self._channel = con


    @kaa.threaded()
    def _tls_server(self, **kwargs):
        ctx = self._make_context(**kwargs)
        con = M2Crypto.SSL.Connection(ctx, self._channel)

        con.setblocking(True)
        con.setup_ssl()
        con.set_accept_state()
        con.accept_ssl()
        con.setblocking(False)

        self._post_check(con, kwargs)
        self._channel = con
        

# XXX: temporary?
TLSSocket = TLSLiteSocket
