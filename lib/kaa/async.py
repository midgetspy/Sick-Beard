# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# async.py - Async callback handling (InProgress)
# -----------------------------------------------------------------------------
# $Id: async.py 4078 2009-05-25 19:02:18Z tack $
#
# -----------------------------------------------------------------------------
# kaa.base - The Kaa Application Framework
# Copyright 2006-2009 Dirk Meyer, Jason Tackaberry, et al.
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

__all__ = [ 'TimeoutException', 'InProgress', 'InProgressCallback',
            'AsyncException', 'InProgressAny', 'InProgressAll', 'InProgressAborted',
            'AsyncExceptionBase', 'make_exception_class', 'inprogress',
            'delay', 'InProgressStatus' ]

# python imports
import sys
import logging
import traceback
import time
import _weakref
import threading

# kaa.base imports
from callback import Callback
from utils import property
from object import Object

# Recursive imports. The Signal requires InProgress which does not
# exist at this point. But async itself does exist. To avoid any
# problems, signal.py can only import async, not InProgress itself.
from signals import Signal

# We have more recursive imports: main, thread, and timer. It is hard
# to fix, but unlike Signal, InProgress needs this during runtime, not
# for class creation. So we import them at the end of this module.

# get logging object
log = logging.getLogger('base.async')


def make_exception_class(name, bases, dict):
    """
    Class generator for AsyncException.  Creates AsyncException class
    which derives the class of a particular Exception instance.
    """
    def create(exc, stack, *args):
        from new import classobj
        e = classobj(name, bases + (exc.__class__,), {})(exc, stack, *args)
        return e

    return create


def inprogress(obj):
    """
    Returns a suitable :class:`~kaa.InProgress` for the given object.

    :param obj: object to represent as an InProgress.
    :return: an :class:`~kaa.InProgress` representing ``obj``
    
    The precise behaviour of an object represented as an
    :class:`~kaa.InProgress` should be defined in the documentation for the
    class.  For example, the :class:`~kaa.InProgress` for a
    :class:`~kaa.Process` object will be finished when the process is
    terminated.
    
    This function simply calls ``__inprogress__()`` of the given ``obj`` if one
    exists, and if not will raise an exception.  In this sense, it behaves
    quite similar to ``len()`` and ``__len__()``.

    It is safe to call this function on InProgress objects.  (The InProgress
    object given will simply be returned.)

    """
    try:
        return obj.__inprogress__()
    except AttributeError:
        raise TypeError("object of type '%s' has no __inprogress__()" % obj.__class__.__name__)


def delay(seconds):
    """
    Returns an InProgress that finishes after the given time in seconds.

    :param obj: object to represent as an InProgress.
    :return: :class:`~kaa.InProgress`
    """
    ip = InProgressCallback()
    timer = OneShotTimer(ip)
    # If the IP gets aborted, stop the timer.  Otherwise the timer
    # will fire and the IP would attempt to get finished a second
    # time (and would therefore raise an exception).
    ip.signals['abort'].connect_weak(lambda exc: timer.stop())
    timer.start(seconds)
    return ip


class AsyncExceptionBase(Exception):
    """
    Base class for asynchronous exceptions.  This class can be used to raise
    exceptions where the traceback object is not available.  The stack is
    stored (which is safe to reference and can be pickled) instead, and when
    AsyncExceptionBase instances are printed, the original traceback will
    be printed.

    This class will proxy the given exception object.
    """
    def __init__(self, exc, stack, *args):
        self._kaa_exc = exc
        self._kaa_exc_stack = stack
        self._kaa_exc_args = args

    def __getattribute__(self, attr):
        # Used by python 2.5, where exceptions are new-style classes.
        if attr.startswith('_kaa'):
            return super(AsyncExceptionBase, self).__getattribute__(attr)
        return getattr(self._kaa_exc, attr)

    def __getattr__(self, attr):
        # Used by python 2.4, where exceptions are old-style classes.
        exc = self._kaa_exc
        if attr == '__members__':
            return [ x for x in dir(exc) if not callable(getattr(exc, x)) ]
        elif attr == '__methods__':
            return [ x for x in dir(exc) if callable(getattr(exc, x)) ]
        return self.__getattribute__(attr)

    def _kaa_get_header(self):
        return 'Exception raised asynchronously; traceback follows:'

    def __str__(self):
        dump = ''.join(traceback.format_list(self._kaa_exc_stack))
        info = '%s: %s' % (self._kaa_exc.__class__.__name__, str(self._kaa_exc))
        return self._kaa_get_header() + '\n' + dump + info


class AsyncException(AsyncExceptionBase):
    __metaclass__ = make_exception_class


class TimeoutException(Exception):
    def __init__(self, msg, inprogress):
        super(TimeoutException, self).__init__(msg)
        self.args = (msg, inprogress)
        self.inprogress = inprogress

    def __getitem__(self, idx):
        return self.args[idx]


class InProgressAborted(BaseException):
    """
    This exception is thrown into an InProgress object when 
    :meth:`~kaa.InProgress.abort` is called.

    For :class:`~kaa.ThreadCallback` and  :class:`~kaa.NamedThreadCallback`
    this exception is raised inside the threaded callback.  This makes
    potentially an asynchronous exception (when used this way), and therefore
    it subclasses BaseException, similar in rationale to KeyboardInterrupt
    and SystemExit, and also (for slightly different reasons) GeneratorExit,
    which as of Python 2.6 also subclasses BaseException.
    """
    pass



class InProgressStatus(Signal):
    """
    Generic progress status object for InProgress. This object can be
    used as 'progress' member of an InProgress object and the caller
    can monitor the progress.
    """
    def __init__(self, max=0):
        super(InProgressStatus, self).__init__()
        self.start_time = time.time()
        self.pos = 0
        self.max = max


    def set(self, pos=None, max=None):
        """
        Set new status. The new status is pos of max.
        """
        if max is not None:
            self.max = max
        if pos is not None:
            self.pos = pos
        if pos > self.max:
            self.max = pos
        self.emit(self)


    def update(self, diff=1):
        """
        Update position by the given difference.
        """
        self.set(self.pos + diff)


    def get_progressbar(self, width=70):
        """
        Return a small ASCII art progressbar.
        """
        n = 0
        if self.max:
            n = int((self.pos / float(self.max)) * (width-3))
        s = '|%%%ss|' % (width-2)
        return s % ("="*n + ">").ljust(width-2)

    @property
    def elapsed(self):
        """
        Return time elapsed since the operation started.
        """
        return time.time() - self.start_time

    @property
    def eta(self):
        """
        Estimated time left to complete the operation. Depends on the
        operation itself if this is correct or not.
        """
        if not self.pos:
            return 0
        sec = (time.time() - self.start_time) / self.pos
        # we assume every step takes the same amount of time
        return sec * (self.max - self.pos)

    @property
    def percentage(self):
        """
        Return percentage of steps done.
        """
        if self.max:
            return (self.pos * 100) / self.max
        return 0


class InProgress(Signal, Object):
    """
    InProgress objects are returned from functions that require more time to
    complete (because they are either blocked on some resource, are executing
    in a thread, or perhaps simply because they yielded control back to the main
    loop as a form of cooperative time slicing).

    InProgress subclasses :class:`~kaa.Signal`, which means InProgress objects are
    themselves signals.  Callbacks connected to an InProgress receive a single
    argument containing the result of the asynchronously executed task.

    If the asynchronous task raises an exception, the
    :attr:`~kaa.InProgress.exception` member, which is a separate signal, is
    emitted instead.
    """
    __kaasignals__ = {
        'abort':
            '''
            Emitted when abort() is called.

            .. describe:: def callback(exc)

               :param exc: an exception object the InProgress was aborted with.
               :type exc: InProgressAborted

            If the task cannot be aborted, the callback can return False, which
            will cause an exception to be raised by abort().
            '''
    }


    def __init__(self, abortable=False, frame=0):
        """
        :param abortable: see the :attr:`~kaa.InProgress.abortable` property.  
                          (Default: False)
        :type abortable: bool
        """
        super(InProgress, self).__init__()
        self._exception_signal = Signal()
        self._finished = False
        self._finished_event = threading.Event()
        self._exception = None
        self._unhandled_exception = None
        # TODO: make progress a property so we can document it.
        self.progress = None
        self.abortable = abortable

        # Stack frame for the caller who is creating us, for debugging.
        self._stack = traceback.extract_stack()[:frame-2]
        self._name = 'owner=%s:%d:%s()' % self._stack[-1][:3]


    def __repr__(self):
        return '<%s object at 0x%08x, %s>' % (self.__class__.__name__, id(self), self._name)


    def __inprogress__(self):
        """
        We subclass Signal which implements this method, but as we are already
        an InProgress, we simply return self.
        """
        return self

    @property
    def exception(self):
        """
        A :class:`~kaa.Signal` emitted when the asynchronous task this InProgress
        represents has raised an exception.

        Callbacks connected to this signal receive three arguments: exception class,
        exception instance, traceback.
        """
        return self._exception_signal


    @property
    def finished(self):
        """
        True if the InProgress is finished.
        """
        return self._finished


    @property
    def result(self):
        """
        The result the InProgress was finished with.  If an exception was thrown
        to the InProgress, accessing this property will raise that exception.
        """
        if not self._finished:
            raise RuntimeError('operation not finished')
        if self._exception:
            self._unhandled_exception = None
            if self._exception[2]:
                # We have the traceback, so we can raise using it.
                exc_type, exc_value, exc_tb_or_stack = self._exception
                raise exc_type, exc_value, exc_tb_or_stack
            else:
                # No traceback, so construct an AsyncException based on the
                # stack.
                raise self._exception[1]

        return self._result


    @property
    def failed(self):
        """
        True if an exception was thrown to the InProgress, False if it was
        finished without error or if it is not yet finished.
        """
        return bool(self._exception)


    # XXX: is this property sane after all?  Maybe there is no such case where
    # an IP can be just ignored upon abort().  kaa.delay() turned out not to be
    # an example after all.
    @property
    def abortable(self):
        """
        True if the asynchronous task this InProgress represents can be
        aborted by a call to :meth:`~kaa.InProgress.abort`.

        Normally :meth:`~kaa.InProgress.abort` will fail if there are no
        callbacks attached to the :attr:`~kaa.InProgress.signals.abort` signal.
        This property may be explicitly set to ``True``, in which case
        :meth:`~kaa.InProgress.abort` will succeed regardless.  An InProgress is
        therefore abortable if the ``abortable`` property has been explicitly
        set to True, if if there are callbacks connected to the
        :attr:`~kaa.InProgress.signals.abort` signal.

        This is useful when constructing an InProgress object that corresponds
        to an asynchronous task that can be safely aborted with no explicit action.
        """
        return self._abortable or self.signals['abort'].count() > 0


    @abortable.setter
    def abortable(self, abortable):
        self._abortable = abortable


    def finish(self, result):
        """
        This method should be called when the owner (creator) of the InProgress is
        finished successfully (with no exception).

        Any callbacks connected to the InProgress will then be emitted with the
        result passed to this method.

        If *result* is an unfinished InProgress, then instead of finishing, we
        wait for the result to finish.

        :param result: the result of the completed asynchronous task.  (This can
                       be thought of as the return value of the task if it had
                       been executed synchronously.)
        :return: This method returns self, which makes it convenient to prime InProgress
                 objects with a finished value. e.g. ``return InProgress().finish(42)``
        """
        if self._finished:
            raise RuntimeError('%s already finished' % self)
        if isinstance(result, InProgress) and result is not self:
            # we are still not finished, wait for this new InProgress
            self.waitfor(result)
            return self

        # store result
        self._finished = True
        self._result = result
        self._exception = None
        # Wake any threads waiting on us
        self._finished_event.set()
        # emit signal
        self.emit_when_handled(result)
        # cleanup
        self.disconnect_all()
        self._exception_signal.disconnect_all()
        self.signals['abort'].disconnect_all()
        return self


    def throw(self, type, value, tb, aborted=False):
        """
        This method should be called when the owner (creator) of the InProgress is
        finished because it raised an exception.

        Any callbacks connected to the :attr:`~kaa.InProgress.exception` signal will
        then be emitted with the arguments passed to this method.

        The parameters correspond to sys.exc_info().

        :param type: the class of the exception
        :param value: the instance of the exception
        :param tb: the traceback object representing where the exception took place
        """
        # This function must deal with a tricky problem.  See:
        # http://mail.python.org/pipermail/python-dev/2005-September/056091.html
        #
        # Ideally, we want to store the traceback object so we can defer the
        # exception handling until some later time.  The problem is that by
        # storing the traceback, we create some ridiculously deep circular
        # references.
        #
        # The way we deal with this is to pass along the traceback object to
        # any handler that can handle the exception immediately, and then
        # discard the traceback.  A stringified formatted traceback is attached
        # to the exception in the formatted_traceback attribute.
        #
        # The above URL suggests a possible non-trivial workaround: create a
        # custom traceback object in C code that preserves the parts of the
        # stack frames needed for printing tracebacks, but discarding objects
        # that would create circular references.  This might be a TODO.

        self._finished = True
        self._exception = type, value, tb
        self._unhandled_exception = True
        stack = traceback.extract_tb(tb)

        # Attach a stringified traceback to the exception object.  Right now,
        # this is the best we can do for asynchronous handlers.
        trace = ''.join(traceback.format_exception(*self._exception)).strip()
        value.formatted_traceback = trace

        # Wake any threads waiting on us.  We've initialized _exception with
        # the traceback object, so any threads that access the result property
        # between now and the end of this function will have an opportunity to
        # get the live traceback.
        self._finished_event.set()

        if self._exception_signal.count() == 0:
            # There are no exception handlers, so we know we will end up
            # queuing the traceback in the exception signal.  Set it to None
            # to prevent that.
            tb = None

        if self._exception_signal.emit_when_handled(type, value, tb) == False:
            # A handler has acknowledged handling this exception by returning
            # False.  So we won't log it.
            self._unhandled_exception = None

        if isinstance(value, InProgressAborted):
            if not aborted:
                # An InProgress we were waiting on has been aborted, so we
                # abort too.
                self.signals['abort'].emit(value)
            self._unhandled_exception = None

        if self._unhandled_exception:
            # This exception was not handled synchronously, so we set up a
            # weakref object with a finalize callback to a function that
            # logs the exception.  We could do this in __del__, except that
            # the gc refuses to collect objects with a destructor.  The weakref
            # kludge lets us accomplish the same thing without actually using
            # __del__.
            #
            # If the exception is passed back via result property, then it is
            # considered handled, and it will not be logged.
            cb = Callback(InProgress._log_exception, trace, value, self._stack)
            self._unhandled_exception = _weakref.ref(self, cb)

        # Remove traceback from stored exception.  If any waiting threads
        # haven't gotten it by now, it's too late.
        if not isinstance(value, AsyncExceptionBase):
            value = AsyncException(value, stack)
        self._exception = value.__class__, value, None

        # cleanup
        self.disconnect_all()
        self._exception_signal.disconnect_all()
        self.signals['abort'].disconnect_all()

        # We return False here so that if we've received a thrown exception
        # from another InProgress we're waiting on, we essentially inherit
        # the exception from it and indicate to it that we'll handle it
        # from here on.  (Otherwise the linked InProgress would figure
        # nobody handled it and would dump out an unhandled async exception.)
        return False

    @classmethod
    def _log_exception(cls, weakref, trace, exc, create_stack):
        """
        Callback to log unhandled exceptions.
        """
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            # We have an unhandled asynchronous SystemExit or KeyboardInterrupt
            # exception.  Rather than logging it, we reraise it in the main
            # loop so that the main loop exception handler can act
            # appropriately.
            def reraise():
                raise exc
            return main.signals['step'].connect_once(reraise)

        log.error('Unhandled %s exception:\n%s', cls.__name__, trace)
        if log.level <= logging.INFO:
            # Asynchronous exceptions create a bit of a problem in that while you
            # know where the exception came from, you don't easily know where it
            # was going.  Here we dump the stack obtained in the constructor,
            # so it's possible to find out which caller didn't properly catch
            # the exception.
            create_tb = ''.join(traceback.format_list(create_stack))
            log.info('Create-stack for InProgress from preceding exception:\n%s', create_tb)


    def abort(self, exc=None):
        """
        Aborts the asynchronous task this InProgress represents.

        :param exc: optional exception object with which to abort the InProgress; if
                    None is given, a general InProgressAborted exception will
                    be used.
        :type exc: InProgressAborted

        Not all such tasks can be aborted.  If aborting is not supported, or if
        the InProgress is already finished, a RuntimeError exception is raised.

        If a coroutine is aborted, the CoroutineInProgress object returned by
        the coroutine will be finished with InProgressAborted, while the underlying
        generator used by the coroutine will have the standard GeneratorExit
        raised inside it.
        """
        if self.finished:
            raise RuntimeError('InProgress is already finished.')

        if exc is None:
            exc = InProgressAborted('InProgress task aborted by abort()')
        elif not isinstance(exc, InProgressAborted):
            raise ValueError('Exception must be instance of InProgressAborted (or subclass thereof)')

        if not self.abortable or self.signals['abort'].emit(exc) == False:
            raise RuntimeError('%s cannot be aborted.' % self)

        self.throw(exc.__class__, exc, None, aborted=True)


    def timeout(self, timeout, callback=None, abort=False):
        """
        Create a new InProgress object linked to this one that will throw
        a TimeoutException if this object is not finished by the given timeout.

        :param callback: called (with no additional arguments) just prior
                         to TimeoutException
        :return: a new :class:`~kaa.InProgress` object that is subject to the timeout

        If the original InProgress finishes before the timeout, the new InProgress
        (returned by this method) is finished with the result of the original.

        If a timeout does occur, the original InProgress object is not affected:
        it is not finished with the TimeoutException, nor is it aborted.  If you
        want to abort the original task you must do it explicitly::

            @kaa.coroutine()
            def read_from_socket(sock):
                try:
                    data = yield sock.read().timeout(3)
                except TimeoutException, (msg, inprogress):
                    print 'Error:', msg
                    inprogress.abort()
        """
        async = InProgress()
        def trigger():
            self.disconnect(async.finish)
            self._exception_signal.disconnect(async.throw)
            if not async._finished:
                if callback:
                    callback()
                msg = 'InProgress timed out after %.02f seconds' % timeout
                async.throw(TimeoutException, TimeoutException(msg, self), None)
                if abort:
                    self.abort()
        async.waitfor(self)
        OneShotTimer(trigger).start(timeout)
        return async


    def execute(self, func, *args, **kwargs):
        """
        Execute the given function and finish the InProgress object with the
        result or exception. 
        
        If the function raises SystemExit or KeyboardInterrupt, those are
        re-raised to allow them to be properly handled by the main loop.

        :param func: the function to be invoked
        :type func: callable
        :param args: the arguments to be passed to the function
        :param kwargs: the keyword arguments to be passed to the function
        :return: the InProgress object being acted upon (self)
        """
        try:
            result = func(*args, **kwargs)
        except BaseException, e:
            self.throw(*sys.exc_info())
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                # Reraise these exceptions to be handled by the mainloop
                raise
        else:
            self.finish(result)
        return self


    def wait(self, timeout=None):
        """
        Blocks until the InProgress is finished.
        
        The main loop is kept alive if waiting in the main thread, otherwise
        the thread is blocked until another thread finishes the InProgress.

        If the InProgress finishes due to an exception, that exception is
        raised.

        :param timeout: if not None, wait() blocks for at most timeout seconds
                        (which may be fractional).  If wait times out, a
                        TimeoutException is raised.
        :return: the value the InProgress finished with
        """
        # Connect a dummy handler to ourselves.  This is a bit kludgy, but
        # solves a particular problem with InProgress(Any|All), which don't
        # actually finish unless something wants to know.  Normally, without
        # wait, we are yielded to the coroutine wrapper which implicitly
        # connects to us.  Here, with wait(), in a sense we want to know when
        # self finishes.
        dummy = lambda *args, **kwargs: None
        self.connect(dummy)

        if is_mainthread():
            # We're waiting in the main thread, so we must keep the mainloop
            # alive by calling main.loop() until we're finished.
            main.loop(lambda: not self.finished, timeout)
        elif not main.is_running():
            # Seems that no loop is running, try to loop
            try:
                main.loop(lambda: not self.finished, timeout)
            except RuntimeError:
                # oops, there is something running, wait
                self._finished_event.wait(timeout)
        else:
            # We're waiting in some other thread, so wait for some other
            # thread to wake us up.
            self._finished_event.wait(timeout)

        if not self.finished:
            self.disconnect(dummy)
            raise TimeoutException

        return self.result


    def waitfor(self, inprogress):
        """
        Connects to another InProgress object (A) to self (B).  When A finishes
        (or throws), B is finished with the result or exception.

        :param inprogress: the other InProgress object to link to.
        :type inprogress: :class:`~kaa.InProgress`
        """
        inprogress.connect_both(self.finish, self.throw)


    def _connect(self, callback, args = (), kwargs = {}, once = False,
                 weak = False, pos = -1):
        """
        Internal connect function. Always set once to True because InProgress
        will be emited only once.
        """
        return Signal._connect(self, callback, args, kwargs, True, weak, pos)


    def connect_both(self, finished, exception=None):
        """
        Convenience function that connects a callback (or callbacks) to both
        the InProgress (for successful result) and exception signals.

        This function does not accept additional args/kwargs to be passed to
        the callbacks.  If you need that, use :meth:`~kaa.InProgress.connect`
        and :attr:`~kaa.InProgress.exception`.connect().

        If *exception* is not given, the given callable will be used for **both**
        success and exception results, and therefore must be able to handle variable
        arguments (as described for each callback below).

        :param finished: callback to be invoked upon successful completion; the
                         callback is passed a single argument, the result returned
                         by the asynchronous task.
        :param exception: (optional) callback to be invoked when the asynchronous task
                          raises an exception; the callback is passed three arguments
                          representing the exception: exception class, exception
                          instance, and traceback.
        """
        if exception is None:
            exception = finished
        self.connect(finished)
        self._exception_signal.connect_once(exception)



class InProgressCallback(InProgress):
    """
    InProgress object that can be used as a callback for an async
    function. The InProgress object will be finished when it is
    called. Special support for Signals that will finish the InProgress
    object when the signal is emited.
    """
    def __init__(self, func=None, abortable=False, frame=0):
        super(InProgressCallback, self).__init__(abortable, frame=frame-1)
        if func is not None:
            # connect self as callback
            func(self)


    def __call__(self, *args, **kwargs):
        """
        Call the InProgressCallback by the external function. This will
        finish the InProgress object.
        """
        # try to get the results as the caller excepts them
        if args and kwargs:
            # no idea how to merge them
            return self.finish((args, kwargs))
        if kwargs and len(kwargs) == 1:
            # return the value
            return self.finish(kwargs.values()[0])
        if kwargs:
            # return as dict
            return self.finish(kwargs)
        if len(args) == 1:
            # return value
            return self.finish(args[0])
        if len(args) > 1:
            # return as list
            return self.finish(args)
        return self.finish(None)


class InProgressAny(InProgress):
    """
    InProgress object that finishes when ANY of the supplied InProgress
    objects (in constructor) finish.  This functionality is useful when
    building state machines using coroutines.

    The initializer can take two optional kwargs: pass_index and filter.

    If pass_index is True, the InProgressAny object then finishes with a
    2-tuple, whose first element is the index (offset from 0) of the InProgress
    that finished, and the second element is the result the InProgress was
    finished with.

    If pass_index is False, the InProgressAny is finished with just the result
    and not the index.

    If filter is specified, it is a callable that receives two arguments,
    the index and finished result (as described above).  If the callable
    returns True AND if there are other underlying InProgress objects that
    could yet be finished, then this InProgressAny is _not_ finished.
    """
    def __init__(self, *objects, **kwargs):
        super(InProgressAny, self).__init__()
        self._pass_index = kwargs.get('pass_index', True)
        self._filter = kwargs.get('filter')

        # Generate InProgress objects for anything that was passed.
        self._objects = [ inprogress(o) for o in objects ]
        self._counter = len(objects) or 1

        self._prefinished_visited = set()
        self._check_prefinished()


    def _get_connect_args(self, ip, n):
        """
        Called for each InProgress we connect to, and returns arguments to be
        passed to self.finish if that InProgress finishes.
        """
        return (n,)


    def _check_prefinished(self):
        """
        Determine if any of the given IP objects were passed to us already finished,
        which may in turn finish us immediately.
        """
        prefinished = []
        for n, ip in enumerate(self._objects):
            if ip.finished and id(ip) not in self._prefinished_visited:
                prefinished.append(n)
                self._prefinished_visited.add(id(ip))
        self._finalize_prefinished(prefinished)


    def _finalize_prefinished(self, prefinished):
        """
        Called from _check_prefinished.  prefinished is a list of indexes
        (relative to self._objects) that were already finished when we tried to
        connect to them.

        This logic is done in a separate method (instead of in _check_prefinished)
        so that subclasses can override this behaviour (without duplicating the
        common code in _check_prefinished).
        """
        if not prefinished:
            return

        # One or more IP was already finished.  We pass each one to
        # self.finish until we're actually finished (because the prefinished
        # IP may get filtered).
        while not self.finished and prefinished:
            idx = prefinished.pop(0)
            ip = self._objects[idx]
            if ip.failed:
                self.finish(True, idx, ip._exception)
            else:
                self.finish(False, idx, ip.result)


    def _changed(self, action):
        """
        Called when a callback connects or disconnects from us.
        """
        if len(self) == 1 and action == Signal.CONNECTED and not self.finished:
            # Someone wants to know when we finish, so now we connect to the
            # underlying InProgress objects to find out when they finish.
            self._check_prefinished()
            for n, ip in enumerate(self._objects):
                if ip.finished:
                    # This one is finished already, no need to connect to it.
                    continue
                args = self._get_connect_args(ip, n)
                ip.connect(self.finish, False, *args).user_args_first = True
                ip.exception.connect(self.finish, True, *args).user_args_first = True

        elif len(self) == 0 and action == Signal.DISCONNECTED:
            for ip in self._objects:
                ip.disconnect(self.finish)
                ip.exception.disconnect(self.finish)

        return super(InProgressAny, self)._changed(action)


    def finish(self, is_exception, index, *result):
        """
        Invoked when any one of the InProgress objects passed to the
        constructor have finished.
        """
        result = result[0] if not is_exception else result
        self._counter -= 1
        if self._filter and self._filter(result) and self._counter > 0:
            # Result is filtered and there are other InProgress candidates,
            # so we'll wait for them.
            return

        super(InProgressAny, self).finish((index, result) if self._pass_index else result)

        # We're done with the underlying IP objects so unref them.  In the
        # case of InProgressCallbacks connected weakly to signals (which
        # happens when signals are given to us on the constructor), they'll
        # get deleted and disconnected from the signals.
        self._objects = None



class InProgressAll(InProgressAny):
    """
    InProgress object that finishes only when ALL of the supplied InProgress
    objects (in constructor) finish.  This functionality is useful when
    building state machines using coroutines.

    The InProgressAll object then finishes with itself (which is really only
    useful when using the Python 2.5 feature of yield return values).  The
    finished InProgressAll is useful to fetch the results of the individual
    InProgress objects.  It can be treated as an iterator, and can be indexed.
    """
    def __init__(self, *objects):
        super(InProgressAll, self).__init__(*objects)

        if not objects:
            self.finish(None)


    def _get_connect_args(self, ip, n):
        return ()


    def _finalize_prefinished(self, prefinished):
        if len(prefinished) == len(self._objects):
            # All underlying InProgress objects are already finished so we're
            # done.  Prime counter to 1 to force finish() to actually finish
            # when we call it next.
            self._counter = 1
            self.finish(False, None)
        elif len(prefinished):
            # Some underlying InProgress objects are already finished so we
            # need to substract them from the number of objects we are still
            # waiting for.
            self._counter -= len(prefinished)


    def finish(self, is_exception, *result):
        self._counter -= 1
        if self._counter == 0:
            super(InProgressAny, self).finish(self)
        # Unlike InProgressAny, we don't unref _objects because the caller
        # may want to access them by iterating us.  That's fine, because
        # unlike InProgressAny where we'd prefer not to have useless
        # transient InProgressCallbacks connected to any provided signals,
        # here we know we won't because they will all have been emitted
        # in order for us to be here.


    def __iter__(self):
        return iter(self._objects)


    def __getitem__(self, idx):
        return self._objects[idx]

# We have some additional modules InProgress needs during
# runtime. They are imported here at the end because these modules
# require InProgress again. Yes, we know, it is a mess. But at least
# we are not importing inside a function which could get us into
# trouble when using threads.
import main
from timer import OneShotTimer
from thread import is_mainthread
