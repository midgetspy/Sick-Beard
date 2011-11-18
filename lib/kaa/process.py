# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# process.py - asynchronous subprocess control via IOChannel
# -----------------------------------------------------------------------------
# $Id: process.py 4080 2009-05-25 19:57:06Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2008-2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'Process', 'supervisor' ]

import subprocess
import os
import shlex
import errno
import logging
import weakref
import signal

from io import IOChannel, IO_WRITE, IO_READ
from signals import Signals
from timer import timed, Timer, OneShotTimer, POLICY_ONCE
from thread import MainThreadCallback, is_mainthread, threaded, MAINTHREAD
from async import InProgress, InProgressAny, InProgressAll, delay, inprogress
from callback import Callback, WeakCallback, CallbackError
from coroutine import coroutine, POLICY_SINGLETON
from utils import property
from object import Object

# get logging object
log = logging.getLogger('base.process')

class _Supervisor(object):
    """
    Supervisor class with which all Process objects register themselves.  The
    Supervisor handles SIGCHLD signals and invokes Process._check_dead of all
    alive Process objects.

    References to all alive Process objects are held by the Supervisor,
    therefore Process objects live as long as the child process remains
    running.
    """
    def __init__(self):
        self.processes = {}

        signal.signal(signal.SIGCHLD, self._sigchld_handler)
        # Set SA_RESTART bit for the signal, which restarts any interrupted
        # system calls -- however, select (at least on Linux) is NOT restarted
        # for reasons described at:
        #    http://lkml.indiana.edu/hypermail/linux/kernel/0003.2/0336.html
        #
        # Therefore the purpose of signal.set_wakeup_fd() eludes me, since
        # select calls get interrupted, there is no need to wake it up.
        try:
            # Python 2.6+
            signal.siginterrupt(signal.SIGCHLD, False)
        except AttributeError:
            try:
                # Python 2.5
                import ctypes
                ctypes.CDLL("libc.so.6").siginterrupt(signal.SIGCHLD, 0)
            except (ImportError, OSError):
                # Python 2.4- is not supported.
                raise SystemError('kaa.base requires Python 2.5 or later')
        

    def register(self, process):
        log.debug('Supervisor now monitoring %s', process)
        self.processes[process] = True


    def unregister(self, process):
        log.debug('Supervisor no longer monitoring %s', process)
        try:
            del self.processes[process]
        except KeyError:
            pass


    @timed(0, timer=OneShotTimer, policy=POLICY_ONCE)
    def _sigchld_handler(self, sig, frame):
        """
        Handler for SIGCHLD.  We invoke this as a OneShotTimer so that we get called
        on the next pass of the mainloop.  If SIGCHLD just interrupted the select
        call in pynotifier, then the following sequence occurs:

           1. SIGCHLD received, and Python's internal C sig handler then
              queues the python handler to run after the bytecode that called
              Python select() completes
           2. low level select() aborts with EINTR (because select ignores
              SA_RESTART bit) and select_error exception is set (but not
              raised into Python yet)
           3. The bytecode responsible for calling select() completes and the
              queued Python SIGCHLD handler is invoked (this is before the
              select_error is raised into Python space).
           4. The @timed decorator wrapper is called (asynchronously), which
              creates a new OneShotTimer to invoke this method
              (_sigchld_handler) in 0s.
           5. Python select() call finally raises select_error with EINTR,
              which is caught and ignored by pynotifier.
           6. pynotifier proceeds to fire any pending timers, and so the timer
              that was just added to call _sigchld_handler is invoked,
              and Bob's your uncle.

        For system calls (such as read()) that _do_ honor the SA_RESTART bit,
        the sequence looks a bit different:

           1. Same #1 as above (except replace select() with whatever system
              call is properly restarted thanks to SA_RESTART)
           2. System call is restarted (presumably within the kernel).
           3. The bytecode responsible for calling the system call completes.
           4. Before the return value is passed back into Python space, the
              queued python handler (@timed decorator wrapper) is called
              asynchronously as in #4 above.
           5. The system call's return value is passed back into Python 
              space as if nothing was interrupted, except now our timer is
              queued.
           6. Next mainloop iteration, select() is called with a 0 timeout;
              then #6 as above.
             
        We _might_ get away fine with not using a timer to call the real
        _sigchld_handler, but as the signal handler is called asynchronously,
        it is safest and most predictable to do as little as possible,
        especially as Process._check_dead() might involve some fairly complex
        paths.
        """
        log.debug('SIGCHLD: entering timed handler')
        for process in self.processes.keys():
            process._check_dead()
        log.debug('SIGCHLD: handler completed')


    def stopall(self, timeout=10):
        """
        Stops all known child processes by calling 
        """
        all = InProgressAll(*[process.stop() for process in self.processes.keys()])
        # Normally we yield InProgressAll objects and they get implicitly connected
        # by the coroutine code.  We're not doing that here, so we connect a dummy
        # handler so the underlying IPs (the processes) get connected to the IPAll.
        all.connect(lambda *args: None)

        # XXX: I've observed SIGCHLD either not be signaled or be missed
        # with stopall() (but not so far any other time).  So this kludge
        # tries to reap all processes every 0.1s while we're killing child
        # processes.
        poll_timer = Timer(lambda: [process._check_dead() for process in self.processes.keys()])
        poll_timer.start(0.1)
        while not all.finished:
            main.step()
        poll_timer.stop()

        # Handle and log any unhandled exceptions from stop() (i.e. child
        # failed to die)
        for process in self.processes:
            try:
                inprogress(process).result
            except SystemError, e:
                log.error(e.message)



supervisor = _Supervisor()

class IOSubChannel(IOChannel):
    """
    Used for stdout and stderr.  Process will connect to *read* and *readline*
    signals for child stdout and stderr, but those connections are internal
    and should not cause the file descriptors to be registered with IOMonitor.
    """
    def __init__(self, process, logger, *args, **kwargs):
        self._process = weakref.ref(process)
        super(IOSubChannel, self).__init__(*args, **kwargs)

        self._logger = logger
        if logger:
            self.signals['read'].connect(logger.write)


    def _is_read_connected(self):
        # With a logger, we'll have 2 signals connect to our 'read' signal: one
        # for the Process's read signal emit, and another for logger.write.
        n = 2 if self._logger else 1
        return len(self._read_signal) > 0 or len(self.signals['read']) > n or \
               (self._process() and len(self._process().signals['read']) > 0)

    def _is_readline_connected(self):
        n = 2 if self._logger else 1
        return len(self._readline_signal) > 0 or len(self.signals['readline']) > n or \
               (self._process() and len(self._process().signals['readline']) > 0)



class Process(Object):

    STATE_STOPPED = 0  # Idle state, no child.
    STATE_RUNNING = 1  # start() was called and child is running
    STATE_STOPPING = 2 # stop() was called
    STATE_DYING = 3    # in the midst of cleanup during child death
    STATE_HUNG = 4     # a SIGKILL failed to stop the process

    __kaasignals__ = {
        'read':
            '''
            Emitted for each chunk of data read from either stdout or stderr
            of the child process.

            .. describe:: def callback(chunk, ...)

               :param chunk: data read from the child's stdout or stderr.
               :type chunk: str

            When a callback is connected to the *read* signal, data is automatically
            read from the child as soon as it becomes available, and the signal
            is emitted.

            It is allowed to have a callback connected to the *read* signal
            and simultaneously use the :meth:`~kaa.Process.read` and
            :meth:`~kaa.Process.readline` methods.
            ''',

        'readline':
            '''
            Emitted for each line read from either stdout or stderr of the
            child process.

            .. describe:: def callback(line, ...)

               :param line: line read from the child's stdout or stderr.
               :type line: str

            It is not allowed to have a callback connected to the *readline* signal
            and simultaneously use the :meth:`~kaa.Process.readline` method.

            Refer to :meth:`~kaa.Process.readline` for more details.
            ''',

        'finished':
            '''
            Emitted when the child is dead and all data from stdout and stderr
            has been consumed.

            .. describe:: def callback(exitcode, ...)

               :param exitcode: the exit code of the child
               :type expected: int

            Due to buffering, a child process may be terminated, but the pipes
            to its stdout and stderr still open possibly containing buffered
            data yet to be read.  This signal emits only when the child has
            exited and all data has been consumed (or stdout and stderr
            explicitly closed).

            After this signal emits, the :attr:`~kaa.Process.readable`
            property will be False.
            ''',

        'exited':
            '''
            Emitted when the child process has terminated.

            .. describe:: def callback(exitcode, ...)

               :param exitcode: the exit code of the child
               :type expected: int

            Unlike the :attr:`~kaa.Process.signals.finished` signal, this
            signal emits when the child is dead (and has been reaped), however
            the Process may or may not still be :attr:`~kaa.Process.readable`.
            '''
    }

    
    def __init__(self, cmd, shell=False, dumpfile=None):
        """
        Create a Process object.  The subprocess is not started until
        :meth:`~kaa.Process.start` is called.

        :param cmd: the command to be executed.
        :type cmd: string or list of strings
        :param shell: True if the command should be executed through a shell.
                      This allows for shell-like syntax (redirection, pipes,
                      etc.), but in this case *cmd* must be a string.
        :type shell: bool
        :param dumpfile: File to which all child stdout and stderr will be
                         dumped, or None to disable output dumping.
        :type dumpfile: None, string (path to filename), file object, IOChannel

        Process objects passed to :func:`kaa.inprogress` return a
        :class:`~kaa.InProgress` that corresponds to the
        :attr:`~kaa.Process.signals.finished` signal (not the
        :attr:`~kaa.Process.signals.exited` signal).
        """
        super(Process, self).__init__()
        self._cmd = cmd
        self._shell = shell
        self._stop_command = None
        # The subprocess.Popen object.
        self._child = None
        # Weakref of self used to invoke Process._cleanup callback on finalization.
        self._cleanup_weakref = None
        # The exit code returned by the child once it completes.
        self._exitcode = None

        if dumpfile:
            # Dumpfile specified, create IOChannel which we'll later pass to
            # IOSubChannels.  dumpfile can be a string (path to file), or
            # anything else you can pass to IOChannel (fd, file-like object,
            # another IOChannel, etc.)
            if isinstance(dumpfile, basestring):
                try:
                    dumpfile = open(dumpfile, 'w')
                    log.info('Logging process activity to %s' % dumpfile.name)
                except IOError:
                    log.warning('Unable to open %s for logging' % dumpfile)
            logger = IOChannel(dumpfile, mode=IO_WRITE)
        else:
            logger = None

        # Create the IOChannels for the child's stdin, stdout, and stderr.
        self._stdin = IOChannel()
        self._stdout = IOSubChannel(self, logger)
        self._stderr = IOSubChannel(self, logger)
        self._weak_closed_cbs = []

        for fd in self._stdout, self._stderr:
            fd.signals['read'].connect_weak(self.signals['read'].emit)
            fd.signals['readline'].connect_weak(self.signals['readline'].emit)
            # We need to keep track of the WeakCallbacks for _cleanup()
            cb = fd.signals['closed'].connect_weak(self._check_dead)
            self._weak_closed_cbs.append(cb)
        self._stdin.signals['closed'].connect_weak(self._check_dead)

        # The Process read and readline signals (aka "global" read/readline signals)
        # encapsulate both stdout and stderr.  When a new callback is connected
        # to these signals, we invoke _update_read_monitor() on the IOSubChannel
        # object which will register the fd with the mainloop if necessary.
        # (If we didn't do this, the fd would not get registered and therefore
        # data never read and therefore the callbacks connected to the global
        # read/readline signals never invoked.)
        cb = WeakCallback(self._update_read_monitor)
        self.signals['read'].changed_cb = cb
        self.signals['readline'].changed_cb = cb

        self._state = Process.STATE_STOPPED 
        # InProgress for the whole process.  Is created in start(), and finished
        # when the process is terminated.
        self._in_progress = None
        

    def _update_read_monitor(self, signal=None, change=None):
        """
        See IOChannel._update_read_monitor for docstring.
        """
        self._stdout._update_read_monitor(signal, change)
        self._stderr._update_read_monitor(signal, change)


    def __inprogress__(self):
        return self._in_progress


    @property
    def stdin(self):
        """
        :class:`~kaa.IOChannel` of child process's stdin.
        
        This object is valid even when the child is not running.
        """
        return self._stdin


    @property
    def stdout(self):
        """
        :class:`~kaa.IOChannel` of child process's stdout.
        
        This object is valid even when the child is not running, although it is
        obviously not readable until the child is started.
        """
        return self._stdout


    @property
    def stderr(self):
        """
        :class:`~kaa.IOChannel` of child process's stderr.
        
        This object is valid even when the child is not running, although it is
        obviously not readable until the child is started.
        """
        return self._stderr


    @property
    def pid(self):
        """
        The child's pid when it is running (or stopping), or None when it is not.
        """
        if self._child:
            return self._child.pid

    @property
    def exitcode(self):
        """
        The child's exit code once it has terminated.
        
        If the child is still running or it has not yet been started, this
        value will be None.
        """
        return self._exitcode


    @property
    def running(self):
        """
        True if the child process is running.

        A child that is currently stopping is still considered running.  When
        the ``running`` property is False, it means :meth:`~kaa.Process.start`
        may safely be called.

        To test whether :meth:`~kaa.Process.read` or :meth:`~kaa.Process.write`
        may be called, use the :attr:`~kaa.Process.readable` and
        :attr:`~kaa.Process.writable` properties respectively.
        """
        return bool(self._child and self._state not in (Process.STATE_STOPPED, Process.STATE_HUNG))


    @property
    def readable(self):
        """
        True if it is possible to read data from the child.

        The child is readable if either the child's stdout or stderr channels
        are still open, or if they are both closed but a read call would
        succeed anyway due to data remaining in the read queue.
        
        This doesn't necessarily mean the child is still running: a terminated
        child may still be read from (there may be data buffered in its stdout
        or stderr channels).  Use the :attr:`~kaa.Process.running` property if
        you want to see if the child is still running.
        """
        return self._stdout.readable or self._stderr.readable


    @property
    def writable(self):
        """
        True if it is possible to write data to the child.

        If the child process is writable, :meth:`~kaa.Process.write` may
        safely be called.  A child that is in the process of stopping is not
        writable.
        """
        return bool(self._child and self._state == Process.STATE_RUNNING)


    @property
    def stop_command(self):
        """
        Stop command for this process.
        
        The command can be either a callable or a string.  The command is
        invoked (if it is a callback) or the command is written to the child's
        stdin (if cmd is a string or unicode) when the process is being
        terminated with a call to stop().

        Shutdown handlers for the process should be set with this property.
        """
        return self._stop_command


    @stop_command.setter
    def stop_command(self, cmd):
        assert(callable(cmd) or type(cmd) in (str, unicode) or cmd == None)
        self._stop_command = cmd


    @property
    def delimiter(self):
        """
        String used to split data for use with :meth:`~kaa.Process.readline`.
        """
        # stdout and stderr are the same.
        return self._stdout.delimiter


    @delimiter.setter
    def delimiter(self, value):
        self._stdout.delimiter = value
        self._stderr.delimiter = value

        
    def _normalize_cmd(self, cmd):
        """
        Returns a list of arguments based on the given cmd.  If cmd is a list,
        empty strings and other zero values are removed and the list is
        returned.  If cmd is a string, it is converted to a list based on shell
        semantics.  

        e.g. program -a "bar baz" \"blah -> ['program', '-a', 'bar baz', '"blah']
        """
        if cmd and isinstance(cmd, basestring):
            return shlex.split(cmd)
        elif isinstance(cmd, (tuple, list)):
            return [ x for x in cmd if cmd ]
        elif not cmd:
            return []

    #@threaded() <-- don't
    def start(self, args=''):
        """
        Starts the process with the given arguments.

        :param args: additional arguments when invoking the child, appended
                     to any arguments specified to the initializer.
        :type args: string or list of strings
        :return: An :class:`~kaa.InProgress` object, finished with the exitcode
                 when the child process terminates.

        The Process is registered with a global supervisor which holds a strong
        reference to the Process object while the child process remains
        active. 

        .. warning::
           If timeout() is called on the returned InProgress and the timeout
           occurs, the InProgress returned by ``start()`` will be finished with
           a TimeoutException even though the child process isn't actually
           dead.  You can always test the :attr:`~kaa.Process.running`
           property, or use the :attr:`~kaa.Process.signals.finished` signal,
           which doesn't emit until the child process is genuinely dead.

        """
        if self._child and self._state != Process.STATE_HUNG:
            raise IOError(errno.EEXIST, 'Child process has already been started')

        if not self._shell:
            cmd = self._normalize_cmd(self._cmd) + self._normalize_cmd(args)
        else:
            # If passing through the shell, user must provide cmd and args 
            # as strings.
            if not isinstance(self._cmd, basestring) or not isinstance(args, basestring):
                raise ValueError('Command and arguments must be strings when shell=True')
            cmd = self._cmd + ' ' + args

        supervisor.register(self)
        log.debug("Spawning: %s", cmd)
        self._child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, close_fds=True, shell=self._shell)

        self._stdin.wrap(self._child.stdin, IO_WRITE)
        self._stdout.wrap(self._child.stdout, IO_READ)
        self._stderr.wrap(self._child.stderr, IO_READ)

        self._in_progress = InProgress()
        self._in_progress.signals['abort'].connect_weak(lambda exc: self.stop())
        self._exitcode = None
        self._state = Process.STATE_RUNNING

        return self._in_progress


    @coroutine(policy=POLICY_SINGLETON)
    def stop(self, cmd=None, wait=3.0):
        """
        Stops the child process.
        
        :param cmd: stop command used to attempt to terminate the child
                    gracefully; overrides the *stop_command* property if
                    specified.
        :type cmd: string or callable; see :attr:`~kaa.Process.stop_command`
        :param wait: number of seconds to wait between termination steps 
                     (see below).
        :type wait: float

        :returns: A :class:`~kaa.InProgress`, finished (with None) when the
                  child terminates.  If the child refuses to terminate (even
                  with a SIGKILL) an SystemError exception is thrown to the
                  InProgress.

        The child process is terminated using the following steps:

            1. The stop command is written (or invoked) if one is specified,
               and up to *wait* seconds is given for the child to terminate.
            2. A SIGTERM is issued to the child process, and, again, we wait up
               to *wait* seconds for the child to terminate.
            3. A SIGKILL is issued to the child process, and this time
               we wait up to *wait*\*2 seconds.

        If after step 3 the child is still not dead, a SystemError exception
        is thrown to the InProgress, as well to the InProgress returned by
        :meth:`~kaa.Process.start` and the *finished* signal will be emitted
        with the value None.
        """
        if self._state != Process.STATE_RUNNING:
            # Process is either stopping or dying (or hung).
            yield

        self._state = Process.STATE_STOPPING
        cmd = cmd or self._stop_command
        pid = self.pid  # See below why we save self.pid

        if cmd:
            log.debug('Stop command specified: %s, stdin=%d', cmd, self._stdin.alive)
            if callable(cmd):
                # XXX: should we allow coroutines for cmd and yield them?
                cmd()
            elif self._stdin.alive:
                # This does get buffered.  We could bypass the write queue
                # by calling self.stdin._write() directly, but maybe the
                # IOChannel isn't writable at this moment.
                self._stdin.write(cmd)

            yield InProgressAny(self._in_progress, delay(wait))
            # If we're here, child is either dead or we timed out.

        self._stdin.close(immediate=True)
        # Either no stop command specified or our stop attempt timed out.
        # Try a relatively polite SIGTERM, then SIGKILL.
        for sig, pause in ((15, wait), (9, wait * 2)):
            if self._state == Process.STATE_STOPPED:
                # And we're done.
                yield
            try:
                os.kill(pid, sig)
                # Here we yield on the 'exited' signal instead of
                # self._in_progress, because the InProgress could in fact be
                # finished due to a timeout, not because the process is
                # legitimately stopped, whereas the 'exited' signals truly is
                # only emitted when the child is dead.  (Also, because we
                # don't care about losing stdout/err data, otherwise we would
                # use 'finished')
                yield InProgressAny(self.signals['exited'], delay(pause))
            except OSError:
                # Process is dead after all.
                self._check_dead()
            except:
                log.exception("Some other error")

        # If state isn't STOPPED, make sure pid hasn't changed.  Because we yield
        # on the 'exited' signal above, it's possible for the user to connect a 
        # callback to 'exited' that restarts the child, which gets executed before
        # this coroutine resumes.  If our pid has changed, we know we died.  If the
        # pid is the same, we have a hung process.
        if self._state != Process.STATE_STOPPED and pid == self.pid:
            # Child refuses to die even after SIGKILL. :(
            self._state = Process.STATE_HUNG
            exc = SystemError('Child process (pid=%d) refuses to die even after SIGKILL' % pid)
            self._in_progress.throw(SystemError, exc, None)
            raise exc


    def _async_read(self, stdout_read, stderr_read):
        """
        Common implementation for read() and readline().
        """
        if not self._stdout.readable and not self._stderr.readable:
            return InProgress().finish(None)

        # TODO: if child is dead, attach handler to this IP and if len data <
        # chunk size, can close the channel.  (What makes this more complicated
        # is knowing which channel to close, given pass_index=False.)
        return InProgressAny(stdout_read(), stderr_read(), pass_index=False,
                             filter=lambda val: val in (None, ''))


    def read(self):
        """
        Reads a chunk of data from either stdout or stderr of the process.

        There is no way to determine from which (stdout or stderr) the data
        was read; if you require this, use the stdout or stderr attributes
        directly (however see warning below).

        :returns: A :class:`~kaa.InProgress`, finished with the data read.
                  If it is finished the empty string, it means the child's
                  stdout and stderr were both closed (which is almost certainly
                  because the process exited) and no data was available.

        No exception is raised if the child is not readable.  Like
        Socket.read(), it is therefore possible to busy-loop by reading on a
        dead child::

            while True:
                data = yield process.read()
                # Or: data = process.read().wait()

        So the return value of read() should be tested for non-None.
        Alternatively, the readable property could be tested::

            while process.readable:
                data = yield process.read()


        .. warning::
           You can read directly from stdout or stderr.  However, beware of this
           code, which is wrong::

               while process.readable:
                   data = yield process.stdout.read()

           In the above incorrect example, process.readable may be True even
           though process.stdout is closed (because process.stderr may not be
           closed).  In this case, process.stdout.read() will finish immediately
           with None, resulting in a busy loop.  The solution is to test the
           process.stdout.readable property instead::

               while process.stdout.readable:
                   data = yield process.stdout.read()
        """
        return self._async_read(self._stdout.read, self._stderr.read)


    def readline(self):
        """
        Reads a line from either stdout or stderr, whichever is available
        first.
        
        If finished with None or the empty string, it means that no data was
        read and the process exited.

        :returns: A :class:`~kaa.InProgress`, finished with the data read.
                  If it is finished the empty string, it means the child's
                  stdout and stderr were both closed (which is almost certainly
                  because the process exited) and no data was available.

        Like :meth:`~kaa.Process.read`, it is possible busy-loop with this
        method, so you should test its output or test the
        :attr:`~kaa.Process.readable` property calling.
        """
        return self._async_read(self._stdout.readline, self._stderr.readline)


    def write(self, data):
        """
        Write data to child's stdin.
        
        Returns an InProgress, which is finished when the data has actually
        been written to the child's stdin.

        :param data: the data to be written to the channel.
        :type data: string

        :returns: An :class:`~kaa.InProgress` object, which is finished when the
                  data has actually been written to the child's stdin.

                  If the channel closes unexpectedly before the data was
                  written, an IOError is thrown to the InProgress.

        This is a convenience function, as the caller could do
        ``process.stdin.write()``.
        """
        if not self._stdin.alive:
            raise IOError(9, 'Cannot write to closed child stdin')
        return self._stdin.write(data)


    def _emit_finished(self):
        if not self._in_progress.finished:
            self._in_progress.finish(self._exitcode)
        self.signals['finished'].emit(self._exitcode)


    def _check_dead(self, expected=None):
        """
        Checks to see if the child process has died.

        This method is called in the following circumstances:
           1. Child is still running and Supervisor invokes it upon SIGCHLD.
           (XX) 2. Child is finished and read() or readline() was called.
           3. One of stdin/stdout/stderr closes on us.
        """
        log.debug('Checking child dead child=%s, state=%d, weakref=%s, stdin=%s, stdout=%s, stderr=%s', self._child,
                  self._state, self._cleanup_weakref, self._stdin.alive, self._stdout.alive, self._stderr.alive)

        if not self._child or self._state in (Process.STATE_STOPPED, Process.STATE_DYING):
            # We're already dead or dying.
            if not self._stdout.alive and not self._stderr.alive and self._cleanup_weakref:
                # Child is dead and all IOChannels are closed.  We no longer need
                # our weakref cleanup crutch.
                self._cleanup_weakref = None
                # With child exited and both stdout/stderr closed, the child is
                # considered finished.
                self._emit_finished()
            return

        if self._child.poll() is not None:
            self._handle_dead()
 

    @classmethod
    def _cleanup(cls, weakref, channels, callbacks):
        """
        Called when the Process object is destroyed (similar to __del__ but
        uses a weakref finalization callback instead to avoid the problems
        associated with __del__).

        The child process may be finished and reaped, but the stdout/stderr
        IOChannels still alive so the caller can retrieve any buffered data
        the child left behind.  However, when the Process object is dead,
        we can close the IOMonitors (which breaks a ref cycle internal to
        IOMonitor).

        We don't worry about stdin because if stdin is alive it means the
        child is still running, and the Supervisor has a reference to us
        and therefore it is impossible for this function to get called.
        """
        log.debug('Process cleanup: stdout=%s stderr=%s', channels[0].fileno, channels[1].fileno)
        for channel, callback in zip(channels, callbacks):
            # We previously attached a weak callback for self._check_dead to
            # the 'closed' signals of stdout and stderr.  Since we're in
            # _cleanup(), it means the Process object is destroyed, and all its
            # weak references are now dead.  When we call close() below, it
            # will emit the 'closed' signal, so our weak _check_dead will be
            # invoked in Signal.emit(), and fail because the weakref is dead.
            #
            # Now normally this isn't a problem, because when weak callbacks
            # die, they automatically get disconnected.  The weak _check_dead
            # callbacks are on the chopping block already, and would get
            # disconnected automatically after this function.  (In other words,
            # _cleanup() is invoked before Signal._weakref_destroyed.)  So
            # we need to disconnect the WeakCallback before invoking close()
            # in order to avoid a CallbackError that Signal.emit() reraises.
            channel.signals['closed'].disconnect(callback)
            channel.close(immediate=True)


    def _handle_dead(self):
        # This state prevents reentry into this method via 'closed' signal
        # of stdin IOChannel.
        self._state = Process.STATE_DYING

        # Should be safe to wait() to collect zombies.  We shouldn't be here
        # unless the process actually is done.
        self._exitcode = self._child.wait()

        log.debug('Child terminated, process=%s exitcode=%d', self, self._exitcode)

        # We can close stdin since the child is dead.  But stdout and stderr
        # need to remain open, in case there is data buffered in them that the
        # user may yet retrieve.
        self._stdin.close(immediate=True)
        self._child = None

        # We no longer need help from the supervisor.  Any future SIGCHLDs
        # are not caused by us.
        supervisor.unregister(self)

        self._state = Process.STATE_STOPPED
        # We don't emit 'finished' here, because stdout/stderr is still open
        # and there may be data yet to be read.  But we do emit 'exited'
        self.signals['exited'].emit(self._exitcode)

        if self._stdout.alive or self._stderr.alive:
            # Use weakref finializer callback kludge to invoke Process._cleanup
            # when Process object goes away in order to close stdout
            # and stderr IOChannels.
            cb = Callback(self.__class__._cleanup, (self._stdout, self._stderr), self._weak_closed_cbs)
            self._cleanup_weakref = weakref.ref(self, cb)
        else:
            # Child exit and stdout/stderr closed.  We're finished.
            self._emit_finished()


# Kludge: import here at the end to avoid cyclical imports.
import main
