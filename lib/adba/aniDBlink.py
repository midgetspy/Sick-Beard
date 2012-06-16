#!/usr/bin/env python
#
# This file is part of aDBa.
#
# aDBa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aDBa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with aDBa.  If not, see <http://www.gnu.org/licenses/>.

import socket, sys, zlib
from time import time, sleep
import threading
from aniDBresponses import ResponseResolver
from aniDBerrors import *


class AniDBLink(threading.Thread):
    def __init__(self, server, port, myport, logFunction, delay=2, timeout=20, logPrivate=False):
        super(AniDBLink, self).__init__()
        self.server = server
        self.port = port
        self.target = (server, port)
        self.timeout = timeout

        self.myport = 0
        self.bound = self.connectSocket(myport, self.timeout)

        self.cmd_queue = {None:None}
        self.resp_tagged_queue = {}
        self.resp_untagged_queue = []
        self.tags = []
        self.lastpacket = time()
        self.delay = delay
        self.session = None
        self.banned = False
        self.crypt = None

        self.log = logFunction
        self.logPrivate = logPrivate

        self._stop = threading.Event()
        self._quiting = False
        self.setDaemon(True)
        self.start()

    def connectSocket(self, myport, timeout):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        portlist = [myport] + [7654]
        for port in portlist:
            try:
                self.sock.bind(('', port))
            except:
                continue
            else:
                self.myport = port
                return True
        else:
            return False;

    def disconnectSocket(self):
        self.sock.close()

    def stop (self):
        self.log("Releasing socket and stopping link thread")
        self._quiting = True
        self.disconnectSocket()
        self._stop.set()

    def stopped (self):
        return self._stop.isSet()

    def print_log(self, data):
        print data

    def print_log_dummy(self, data):
        pass

    def run(self):
        while not self._quiting:
            try:
                data = self.sock.recv(8192)
            except socket.timeout:
                self._handle_timeouts()

                continue
            self.log("NetIO < %s" % repr(data))
            try:
                for i in range(2):
                    try:
                        tmp = data
                        resp = None
                        if tmp[:2] == '\x00\x00':
                            tmp = zlib.decompressobj().decompress(tmp[2:])
                            self.log("UnZip | %s" % repr(tmp))
                        resp = ResponseResolver(tmp)
                    except:
                        sys.excepthook(*sys.exc_info())
                        self.crypt = None
                        self.session = None
                    else:
                        break
                if not resp:
                    raise AniDBPacketCorruptedError, "Either decrypting, decompressing or parsing the packet failed"
                cmd = self._cmd_dequeue(resp)
                resp = resp.resolve(cmd)
                resp.parse()
                if resp.rescode in ('200', '201'):
                    self.session = resp.attrs['sesskey']
                if resp.rescode in ('209',):
                    print "sorry encryption is not supported"
                    raise
                    #self.crypt=aes(md5(resp.req.apipassword+resp.attrs['salt']).digest())
                if resp.rescode in ('203', '403', '500', '501', '503', '506'):
                    self.session = None
                    self.crypt = None
                if resp.rescode in ('504', '555'):
                    self.banned = True
                    print "AniDB API informs that user or client is banned:", resp.resstr
                resp.handle()
                if not cmd or not cmd.mode:
                    self._resp_queue(resp)
                else:
                    self.tags.remove(resp.restag)
            except:
                sys.excepthook(*sys.exc_info())
                print "Avoiding flood by paranoidly panicing: Aborting link thread, killing connection, releasing waiters and quiting"
                self.sock.close()
                try:cmd.waiter.release()
                except:pass
                for tag, cmd in self.cmd_queue.iteritems():
                    try:cmd.waiter.release()
                    except:pass
                sys.exit()

    def _handle_timeouts(self):
        willpop = []
        for tag, cmd in self.cmd_queue.iteritems():
            if not tag:
                continue
            if time() - cmd.started > self.timeout:
                self.tags.remove(cmd.tag)
                willpop.append(cmd.tag)
                cmd.waiter.release()

        for tag in willpop:
            self.cmd_queue.pop(tag)

    def _resp_queue(self, response):
        if response.restag:
            self.resp_tagged_queue[response.restag] = response
        else:
            self.resp_untagged_queue.append(response)

    def getresponse(self, command):
        if command:
            resp = self.resp_tagged_queue.pop(command.tag)
        else:
            resp = self.resp_untagged_queue.pop()
        self.tags.remove(resp.restag)
        return resp

    def _cmd_queue(self, command):
        self.cmd_queue[command.tag] = command
        self.tags.append(command.tag)

    def _cmd_dequeue(self, resp):
        if not resp.restag:
            return None
        else:
            return self.cmd_queue.pop(resp.restag)

    def _delay(self):
        return (self.delay < 2.1 and 2.1 or self.delay)

    def _do_delay(self):
        age = time() - self.lastpacket
        delay = self._delay()
        if age <= delay:
            sleep(delay - age)

    def _send(self, command):
        if self.banned:
            self.log("NetIO | BANNED")
            raise AniDBBannedError, "Not sending, banned"
        self._do_delay()
        self.lastpacket = time()
        command.started = time()
        data = command.raw_data()

        self.sock.sendto(data, self.target)
        if command.command == 'AUTH' and self.logPrivate:
            self.log("NetIO > sensitive data is not logged!")
        else:
            self.log("NetIO > %s" % repr(data))

    def new_tag(self):
        if not len(self.tags):
            maxtag = "T000"
        else:
            maxtag = max(self.tags)
        newtag = "T%03d" % (int(maxtag[1:]) + 1)
        return newtag

    def request(self, command):
        if not (self.session and command.session) and command.command not in ('AUTH', 'PING', 'ENCRYPT'):
            raise AniDBMustAuthError, "You must be authed to execute commands besides AUTH and PING"
        command.started = time()
        self._cmd_queue(command)
        self._send(command)
