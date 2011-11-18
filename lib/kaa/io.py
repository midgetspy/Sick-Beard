# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# io.py - I/O management for the Kaa Framework
# -----------------------------------------------------------------------------
# $Id: io.py 4070 2009-05-25 15:32:31Z tack $
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

__all__ = [ 'IO_READ', 'IO_WRITE', 'IOMonitor', 'WeakIOMonitor', 'IOChannel' ]

import sys
import os
import socket
import logging
import time
import fcntl
import cStringIO
import re

import nf_wrapper as notifier
from callback import WeakCallback
from signals import Signal
from thread import MainThreadCallback, is_mainthread
from async import InProgress, inprogress
from utils import property
from object import Object
# Note: recursive imports are handled at the end of this module.

# get logging object
log = logging.getLogger('base.io')

IO_READ   = 1
IO_WRITE  = 2

class IOMonitor(notifier.NotifierCallback):
    def __init__(self, callback, *args, **kwargs):
        """
        Creates an IOMonitor to monitor IO activity via the mainloop.
        
        Once a file descriptor is registered using the
        :meth:`~kaa.IOMonitor.register` method, the given *callback* is invoked
        upon I/O activity.
        """
        super(IOMonitor, self).__init__(callback, *args, **kwargs)
        self.ignore_caller_args = True


    def register(self, fd, condition = IO_READ):
        """
        Register the IOMonitor to a specific file descriptor.

        The IOMonitor is registered with the notifier, which means that the
        notifier holds a reference to the IOMonitor until it is explicitly
        unregistered (or until the file descriptor is closed).

        :param fd: The file descriptor to monitor.
        :type fd: File descriptor or any file-like object
        :param condition: IO_READ or IO_WRITE
        """
        if self.active:
            if fd != self._id or condition != self._condition:
                raise ValueError('Existing file descriptor already registered with this IOMonitor.')
            return
        if not is_mainthread():
            return MainThreadCallback(self.register)(fd, condition)
        notifier.socket_add(fd, self, condition-1)
        self._condition = condition
        # Must be called _id to correspond with base class.
        self._id = fd


    def unregister(self):
        """
        Unregister the IOMonitor
        """
        if not self.active:
            return
        if not is_mainthread():
            return MainThreadCallback(self.unregister)()
        notifier.socket_remove(self._id, self._condition-1)
        super(IOMonitor, self).unregister()



class WeakIOMonitor(notifier.WeakNotifierCallback, IOMonitor):
    """
    IOMonitor using weak references for the callback.

    Any previously registered file descriptor will become unregistered from
    the notifier when the callback (or any arguments) are destroyed.
    """
    pass


class IOChannel(Object):
    """
    Base class for read-only, write-only or read-write descriptors such as
    Socket and Process.  Implements logic common to communication over
    such channels such as async read/writes and read/write buffering.

    It may also be used directly with file descriptors or file-like objects.
    e.g. ``IOChannel(file('somefile'))``

    :param channel: file descriptor to wrap into an IOChannel
    :type channel: integer file descriptor, file-like object, or other IOChannel
    :param mode: indicates whether the channel is readable, writable, or both.
    :type mode: bitmask of kaa.IO_READ and/or kaa.IO_WRITE
    :param chunk_size: maximum number of bytes to be read in from the channel
                       at a time; defaults to 1M.
    :param delimiter: string used to split data for use with readline; defaults
                      to '\\\\n'.

    Writes may be performed to an IOChannel that is not yet open.  These writes
    will be queued until the queue size limit (controlled by the
    :attr:`~kaa.IOChannel.queue_size` property) is reached, after which an
    exception will be raised.  The write queue will be written to the channel
    once it becomes writable.

    Reads are asynchronous and non-blocking, and may be performed using two
    possible approaches:

        1. Connecting a callback to the :attr:`~kaa.IOChannel.signals.read` 
           or :attr:`~kaa.IOChannel.signals.readline` signals.
        2. Invoking the :meth:`~kaa.IOChannel.read` or
           :meth:`~kaa.IOChannel.readline` methods, which return
           :class:`~kaa.InProgress` objects.

    It is not possible to use both approaches with readline.  (That is, it
    is not permitted to connect a callback to the *readline* signal and
    subsequently invoke the :meth:`~kaa.IOChannel.readline` method when the
    callback is still connected.)

    However, :meth:`~kaa.IOChannel.read` and :meth:`~kaa.IOChannel.readline`
    will work predictably when a callback is connected to the *read* signal.
    Such a callback always receives all data from the channel once connected,
    but will not interfere with (or "steal" data from) calls to read() or
    readline().

    Data is not consumed from the channel if no one is interested in reads
    (that is, when there are no read() or readline() calls in progress, and
    there are no callbacks connected to the *read* and *readline* signals).
    This is necessary for flow control.

    Data is read from the channel in chunks, with the maximum chunk being
    defined by the :attr:`~kaa.IOChannel.queue_size` property.  Unlike other
    APIs, read() does not block and will not consume all data to the end of the
    channel, but rather returns between 0 and *chunk_size* bytes when it
    becomes available.  If read() returns a zero-byte string, it means the
    channel is closed.  (Here, "returns X" means the :class:`~kaa.InProgress`
    object read() actually returns is finished with X.)

    In order for readline to work properly, a read queue is maintained, which
    may grow up to *queue_size*.  See the :meth:`~kaa.IOChannel.readline` method
    for more details.
    """
    __kaasignals__ = {
        'read':
            '''
            Emitted for each chunk of data read from the channel.

            .. describe:: def callback(chunk, ...)

               :param chunk: data read from the channel
               :type chunk: str

            When a callback is connected to the *read* signal, data is automatically
            read from the channel as soon as it becomes available, and the signal
            is emitted.

            It is allowed to have a callback connected to the *read* signal
            and simultaneously use the :meth:`~kaa.IOChannel.read` and
            :meth:`~kaa.IOChannel.readline` methods.
            ''',

        'readline':
            '''
            Emitted for each line read from the channel.

            .. describe:: def callback(line, ...)

               :param line: line read from the channel
               :type line: str

            It is not allowed to have a callback connected to the *readline* signal
            and simultaneously use the :meth:`~kaa.IOChannel.readline` method.

            Refer to :meth:`~kaa.IOChannel.readline` for more details.
            ''',

        'closed':
            '''
            Emitted when the channel is closed.

            .. describe:: def callback(expected, ...)

               :param expected: True if the channel is closed because
                                :meth:`~kaa.IOChannel.close` was called.
               :type expected: bool
            '''
    }

    def __init__(self, channel=None, mode=IO_READ|IO_WRITE, chunk_size=1024*1024, delimiter='\n'):
        super(IOChannel, self).__init__()
        self._delimiter = delimiter
        self._write_queue = []
        # Read queue used for read() and readline(), and 'readline' signal.
        self._read_queue = cStringIO.StringIO()
        # Number of bytes each queue (read and write) are limited to.
        self._queue_size = 1024*1024
        self._chunk_size = chunk_size
        self._queue_close = False
    
        # Internal signals for read() and readline()  (these are different from
        # the same-named public signals as they get emitted even when data is
        # None.  When these signals get updated, we call _update_read_monitor
        # to register the read IOMonitor.
        cb = WeakCallback(self._update_read_monitor)
        self._read_signal = Signal(cb)
        self._readline_signal = Signal(cb)
        self.signals['read'].changed_cb = cb
        self.signals['readline'].changed_cb = cb

        # These variables hold the IOMonitors for monitoring; we only allocate
        # a monitor when the channel is connected to avoid a ref cycle so that
        # disconnected channels will get properly deleted when they are not
        # referenced.
        self._rmon = None
        self._wmon = None

        self.wrap(channel, mode)


    def __repr__(self):
        clsname = self.__class__.__name__
        if not hasattr(self, '_channel') or not self._channel:
            return '<kaa.%s - disconnected>' % clsname
        return '<kaa.%s fd=%d>' % (clsname, self.fileno)


    @property
    def alive(self):
        """
        True if the channel exists and is open.
        """
        # If the channel is closed, self._channel will be None.
        return self._channel != None


    @property
    def readable(self):
        """
        True if the channel is open, or if the channel is closed but a read
        call would still succeed (due to buffered data).

        Note that a value of True does not mean there **is** data available, but
        rather that there could be and that a read() call is possible (however
        that read() call may return None, in which case the readable property
        will subsequently be False).
        """
        return self._channel != None or self._read_queue.tell() > 0


    @property
    def writable(self):
        """
        True if write() may be called.
        
        (However, if you pass too much data to write() such that the write
        queue limit is exceeded, the write will fail.)
        """
        # By default, this is always True regardless if the channel is open, so
        # long as there is space available in the write queue, but subclasses
        # may want to override.
        return self.write_queue_used < self._queue_size


    @property
    def fileno(self):
        """
        The file descriptor (integer) for this channel, or None if no channel
        has been set.
        """
        try:
            return self._channel.fileno()
        except (ValueError, AttributeError):
            # AttributeError: probably not a file object (doesn't have fileno() anyway)
            # ValueError: probably "I/O operation on a closed file"
            return self._channel


    @property
    def chunk_size(self):
        """
        Number of bytes to attempt to read from the channel at a time.
        
        The default is 1M.  A 'read' signal is emitted for each chunk read from
        the channel.  (The number of bytes read at a time may be less than the
        chunk size, but will never be more.)
        """
        return self._chunk_size


    @chunk_size.setter
    def chunk_size(self, size):
        self._chunk_size = size


    @property
    def queue_size(self):
        """
        The size limit in bytes for the read and write queues.
        
        Each queue can consume at most this size plus the chunk size.  Setting
        a value does not affect any data currently in any of the the queues.
        """
        return self._queue_size


    @queue_size.setter
    def queue_size(self, value):
        self._queue_size = value


    @property
    def write_queue_used(self):
        """
        The number of bytes queued in memory to be written to the channel.
        """
        # XXX: this is not terribly efficient when the write queue has
        # many elements.  We may decide to keep a separate counter.
        return sum(len(data) for data, inprogress in self._write_queue)


    @property
    def read_queue_used(self):
        """
        The number of bytes in the read queue.
        
        The read queue is only used if either readline() or the readline signal
        is.
        """
        return self._read_queue.tell()

    @property
    def delimiter(self):
        """
        String used to split data for use with :meth:`~kaa.IOChannel.readline`.

        Delimiter may also be a list of strings, in which case any one of the
        elements in the list will be used as a delimiter.  For example, if you
        want to delimit based on either \\\\r or \\\\n, specify ['\\\\r', '\\\\n'].
        """
        return self._delimiter


    @delimiter.setter
    def delimiter(self, value):
        self._delimiter = value


    def _is_read_connected(self):
        """
        Returns True if an outside caller is interested in reads (not readlines).
        """
        return not len(self._read_signal) == len(self.signals['read']) == 0


    def _is_readline_connected(self):
        """
        Returns True if an outside caller is interested in readlines (not reads).
        """
        return not len(self._readline_signal) == len(self.signals['readline']) == 0


    def _update_read_monitor(self, signal=None, change=None):
        """
        Update read IOMonitor to register or unregister based on if there are
        any handlers attached to the read signals.  If there are no handlers,
        there is no point in reading data from the channel since it will go 
        nowhere.  This also allows us to push back the read buffer to the OS.

        We must call this immediately after reading a block, and not defer
        it until the end of the mainloop iteration via a timer in order not
        to lose incoming data between read() calls.
        """
        if not (self._mode & IO_READ) or not self._rmon:
            return
        elif not self._is_read_connected() and not self._is_readline_connected():
            self._rmon.unregister()
        elif not self._rmon.active:
            self._rmon.register(self.fileno, IO_READ)


    def _set_non_blocking(self):
        """
        Low-level call to set the channel non-blocking.  Can be overridden by
        subclasses.
        """
        flags = fcntl.fcntl(self.fileno, fcntl.F_GETFL)
        fcntl.fcntl(self.fileno, fcntl.F_SETFL, flags | os.O_NONBLOCK)


    def wrap(self, channel, mode):
        """
        Make the IOChannel represent a new descriptor or file-like object.
        
        This is implicitly called by the initializer.  If the IOChannel is
        already wrapping another channel, it will be closed before the given
        one is wrapped.
        
        :param channel: file descriptor to wrap into the IOChannel
        :type channel: integer file descriptor, file-like object, or 
                       other IOChannel
        :param mode: indicates whether the channel is readable, writable,
                     or both.
        :type mode: bitmask of kaa.IO_READ and/or kaa.IO_WRITE
        """
        if hasattr(self, '_channel') and self._channel:
            # Wrapping a new channel while an existing one is open, so close
            # the existing one.
            self.close(immediate=True)

        if isinstance(channel, IOChannel):
            # Given channel is itself another IOChannel.  Wrap its underlying
            # channel (file descriptor or other file-like object).
            channel = channel._channel

        self._channel = channel
        self._mode = mode
        if not channel:
            return
        self._set_non_blocking()

        if self._rmon:
            self._rmon.unregister()
            self._rmon = None
        if self._wmon:
            self._wmon.unregister()
            self._wmon = None

        if self._mode & IO_READ:
            self._rmon = IOMonitor(self._handle_read)
            self._update_read_monitor()
        if self._mode & IO_WRITE:
            self._wmon = IOMonitor(self._handle_write)
            if self._write_queue:
                self._wmon.register(self.fileno, IO_WRITE)

        # Disconnect channel on shutdown.
        #
        # XXX: actually, don't.  If a Process object has a stop command, we
        # need stdin alive so we can send it.  Even if it doesn't have a stop
        # command, closing the stdin pipe to child processes seems to sometimes
        # do undesirable things.  For example, MPlayer will leave one of its
        # threads running, even though the main thread dies.)
        #
        # If it turns out we do need a shutdown handler for IOChannels,
        # make it opt-in and clearly document why.
        #
        #main.signals['shutdown'].connect_weak(self.close)


    def _clear_read_queue(self):
        self._read_queue.seek(0)
        self._read_queue.truncate()


    def _find_delim(self, buf, start=0):
        """
        Returns the position in the buffer where the first delimiter is found.
        The index position includes the delimiter.  If the delimiter is not
        found, None is returned.
        """
        if isinstance(self._delimiter, basestring):
            idx = buf.find(self._delimiter, start)
            return idx + len(self._delimiter) if idx >= 0 else None

        # Delimiter is a list, so find any one of them.
        m = re.compile('|'.join(self._delimiter)).search(buf, start)
        return m.end() if m else None


    def _pop_line_from_read_queue(self):
        """
        Pops a line (plus delimiter) from the read queue.  If the delimiter
        is not found in the queue, returns None.
        """
        s = self._read_queue.getvalue()
        idx = self._find_delim(s)
        if idx is None:
            return
 
        self._clear_read_queue()
        self._read_queue.write(s[idx:])
        return s[:idx]


    def _async_read(self, signal):
        """
        Common implementation for read() and readline().
        """
        if not (self._mode & IO_READ):
            raise IOError(9, 'Cannot read on a write-only channel')
        if not self.readable:
            # channel is not readable.  Return an InProgress pre-finished
            # with None
            return InProgress().finish(None)

        ip = inprogress(signal)

        def abort(exc):
            # XXX: closure around ip and signal holds strong refs; is this bad?
            signal.disconnect(ip)
            self._update_read_monitor()

        ip.signals['abort'].connect(abort)
        return ip


    def read(self):
        """
        Reads a chunk of data from the channel.
        
        :returns: An :class:`~kaa.InProgress` object. If the InProgress is
                  finished with the empty string, it means that no data 
                  was collected and the channel was closed (or the channel 
                  was already closed when read() was called).

        It is therefore possible to busy-loop by reading on a closed channel::

            while True:
                data = yield channel.read()
                # Or: channel.read().wait()

        So the return value of read() should be checked.  Alternatively,
        channel.readable could be tested::

            while channel.readable:
                 data = yield process.read()

        """
        if self._read_queue.tell() > 0:
            s = self._read_queue.getvalue()
            self._clear_read_queue()
            return InProgress().finish(s)

        return self._async_read(self._read_signal)


    def readline(self):
        """
        Reads a line from the channel.
        
        The line delimiter is included in the string to avoid ambiguity.  If no
        delimiter is present then either the read queue became full or the
        channel was closed before a delimiter was received.

        :returns: An :class:`~kaa.InProgress` object. If the InProgress is
                  finished with the empty string, it means that no data 
                  was collected and the channel was closed (or the channel 
                  was already closed when readline() was called).

        Data from the channel is read and queued in until the delimiter (\\\\n by
        default, but may be changed by the :attr:`~kaa.IOChannel.delimiter`
        property) is found.  If the read queue size exceeds the queue limit,
        then the InProgress returned here will be finished prematurely with
        whatever is in the read queue, and the read queue will be purged.

        This method may not be called when a callback is connected to the
        IOChannel's readline signal.  You must use either one approach or the
        other.
        """
        if self._is_readline_connected() and len(self._readline_signal) == 0:
            # Connecting to 'readline' signal _and_ calling readline() is
            # not supported.  It's unclear how to behave in this case.
            raise RuntimeError('Callback currently connected to readline signal')

        line = self._pop_line_from_read_queue()
        if line:
            return InProgress().finish(line)
        return self._async_read(self._readline_signal)


    def _read(self, size):
        """
        Low-level call to read from channel.  Can be overridden by subclasses.
        Must return a string of at most size bytes, or the empty string or
        None if no data is available.
        """
        try:
            return self._channel.read(size)
        except AttributeError:
            return os.read(self.fileno, size)


    def _handle_read(self):
        """
        IOMonitor callback when there is data to be read from the channel.
        
        This callback is only registered when we know the user is interested in
        reading data (by connecting to the read or readline signals, or calling
        read() or readline()).  This is necessary for flow control.
        """
        try:
            data = self._read(self._chunk_size)
            log.debug("IOChannel read data: channel=%s fd=%s len=%d" % (self._channel, self.fileno, len(data)))
        except (IOError, socket.error), (errno, msg):
            if errno == 11:
                # Resource temporarily unavailable -- we are trying to read
                # data on a socket when none is available.
                return
            # If we're here, then the socket is likely disconnected.
            data = None
        except Exception:
            log.exception('%s._handle_read failed, closing socket', self.__class__.__name__)
            data = None

        if not data:
            # No data, channel is closed.  IOChannel.close will emit signals
            # used for read() and readline() with any data left in the read
            # queue in order to finish any InProgress waiting.
            return self.close(immediate=True, expected=False)

        # _read_signal is for InProgress objects waiting on the next read().
        self._read_signal.emit(data)
        self.signals['read'].emit(data)
 
        if self._is_readline_connected():
            if len(self._readline_signal) == 0:
                # Callback is connected to the 'readline' signal, so loop
                # through read queue and emit all lines individually.
                queue = self._read_queue.getvalue() + data
                self._clear_read_queue()

                lines, last, idx = [], 0, self._find_delim(queue)
                while True:
                    # If idx is None, it will slice to the end.
                    lines.append(queue[last:idx])
                    if idx is None:
                        break
                    last = idx
                    idx = self._find_delim(queue, last)

                if self._find_delim(lines[-1]) is None:
                    # Queue did not end with delimiter, so push the remainder back.
                    self._read_queue.write(lines.pop())

                for line in lines:
                    self.signals['readline'].emit(line)

            else:
                # No callbacks connected to 'readline' signal, here we handle
                # a single readline() call.
                if self.read_queue_used + len(data) > self._queue_size:
                    # This data chunk would exceed the read queue limit.  We
                    # instead emit whatever's in the read queue, and then start
                    # it over with this chunk.
                    # TODO: it's possible this chunk contains the delimiter we've
                    # been waiting for.  If so, we could salvage things.
                    line = self._read_queue.getvalue()
                    self._clear_read_queue()
                    self._read_queue.write(data)
                else:
                    self._read_queue.write(data)
                    line = self._pop_line_from_read_queue()

                if line is not None:
                    self._readline_signal.emit(line)

        # Update read monitor if necessary.  If there are no longer any
        # callbacks left on any of the read signals (most likely _read_signal
        # or _readline_signal), we want to prevent _handle_read() from being
        # called, otherwise next time read() or readline() is called, we will
        # have lost that data.
        self._update_read_monitor()


    def _write(self, data):
        """
        Low-level call to write to the channel  Can be overridden by subclasses.
        Must return number of bytes written to the channel.
        """
        return os.write(self.fileno, data)


    def write(self, data):
        """
        Writes the given data to the channel.
        
        :param data: the data to be written to the channel.
        :type data: string

        :returns: An :class:`~kaa.InProgress` object which is finished when the
                  given data is fully written to the channel.  The InProgress
                  is finished with the number of bytes sent in the last write 
                  required to commit the given data to the channel.  (This may
                  not be the actual number of bytes of the given data.)

                  If the channel closes unexpectedly before the data was
                  written, an IOError is thrown to the InProgress.

        It is not required that the channel be open in order to write to it.
        Written data is queued until the channel open and then flushed.  As
        writes are asynchronous, all written data is queued.  It is the
        caller's responsibility to ensure the internal write queue does not
        exceed the desired size by waiting for past write() InProgress to
        finish before writing more data.

        If a write does not complete because the channel was closed
        prematurely, an IOError is thrown to the InProgress.
        """
        if not (self._mode & IO_WRITE):
            raise IOError(9, 'Cannot write to a read-only channel')
        if not self.writable:
            raise IOError(9, 'Channel is not writable')
        if self.write_queue_used + len(data) > self._queue_size:
            raise ValueError('Data would exceed write queue limit')

        inprogress = InProgress()
        if data:
            def abort(exc):
                try:
                    self._write_queue.remove((data, inprogress))
                except ValueError:
                    # Too late to abort.
                    return False
            inprogress.signals['abort'].connect(abort)
            self._write_queue.append((data, inprogress))
            if self._channel and self._wmon and not self._wmon.active:
                self._wmon.register(self.fileno, IO_WRITE)
        else:
            # We're writing the null string, nothing really to do.  We're
            # implicitly done.
            inprogress.finish(0)
        return inprogress


    def _handle_write(self):
        """
        IOMonitor callback when the channel is writable.  This callback is not
        registered then the write queue is empty, so we only get called when
        there is something to write.
        """
        if not self._write_queue:
            # Can happen if a write was aborted.
            return

        try:
            while self._write_queue:
                data, inprogress = self._write_queue.pop(0)
                sent = self._write(data)
                if sent != len(data):
                    # Not all data was able to be sent; push remaining data
                    # back onto the write buffer.
                    self._write_queue.insert(0, (data[(sent if sent >= 0 else 0):], inprogress))
                    break
                else:
                    # All data is written, finish the InProgress associated
                    # with this write.
                    inprogress.finish(sent)

            if not self._write_queue:
                if self._queue_close:
                    return self.close(immediate=True)
                self._wmon.unregister()

        except Exception, e:
            tp, exc, tb = sys.exc_info()
            if tp in (OSError, IOError, socket.error) and e.args[0] == 11:
                # Resource temporarily unavailable -- we are trying to write
                # data to a socket which is not ready.  To prevent a busy loop
                # (mainloop will keep calling us back) we sleep a tiny
                # bit.  It's admittedly a bit kludgy, but it's a simple
                # solution to a condition which should not occur often.
                self._write_queue.insert(0, (data, inprogress))
                time.sleep(0.001)
                return

            if tp in (IOError, socket.error, OSError):
                # Any of these are treated as fatal.  We close, which
                # also throws to any other pending InProgress writes.
                self.close(immediate=True, expected=False)
                # Normalize exception into an IOError.
                tp, exc = IOError, IOError(*e.args)
    
            # Throw the current exception to the InProgress for this write.
            # If nobody is listening for it, it will eventually get logged
            # as unhandled.
            inprogress.throw(tp, exc, tb)

            # XXX: this seems to be necessary in order to get the unhandled
            # InProgress to log, but I've no idea why.
            del inprogress


    def _close(self):
        """
        Low-level call to close the channel.  Can be overridden by subclasses.
        """
        try:
            self._channel.close()
        except AttributeError:
            os.close(self.fileno)


    def close(self, immediate=False, expected=True):
        """
        Closes the channel.
        
        :param immediate: if False and there is data in the write buffer, the
                          channel is closed once the write buffer is emptied.
                          Otherwise the channel is closed immediately and the 
                          *closed* signal is emitted.
        :type immediate: bool
        """
        log.debug('IOChannel closed: channel=%s, immediate=%s, fd=%s', self, immediate, self.fileno)
        if not immediate and self._write_queue:
            # Immediate close not requested and we have some data left
            # to be written, so defer close until after write queue
            # is empty.
            self._queue_close = True
            return

        if not self._rmon and not self._wmon:
            # already closed
            return

        if self._rmon:
            self._rmon.unregister()
        if self._wmon:
            self._wmon.unregister()
        self._rmon = None
        self._wmon = None
        self._queue_close = False

        # Finish any InProgress waiting on read() or readline() with whatever
        # is left in the read queue.
        s = self._read_queue.getvalue()
        self._read_signal.emit(s)
        self._readline_signal.emit(s)
        self._clear_read_queue()

        # Throw IOError to any pending InProgress in the write queue
        for data, inprogress in self._write_queue:
            if len(inprogress):
                # Somebody cares about this InProgress, so we need to finish
                # it.
                inprogress.throw(IOError, IOError(9, 'Channel closed prematurely'), None)
        del self._write_queue[:]

        try:
            self._close()
        except (IOError, socket.error), (errno, msg):
            # Channel may already be closed, which is ok.
            if errno != 9:
                # It isn't, this is some other error, so reraise exception.
                raise
        finally:
            self._channel = None

            self.signals['closed'].emit(expected)
            # We aren't attaching to 'shutdown' in wrap() after all.  Comment
            # out for now.
            #main.signals['shutdown'].disconnect(self.close)


# We have have a problem with recursive imports. We need main here,
# but main depends (through various other modules) on io.py. Since we
# only need main during runtime, we import it at the end of this
# module.
import main
