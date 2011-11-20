# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# coroutine.py - coroutine decorator and helper functions
# -----------------------------------------------------------------------------
# $Id: coroutine.py 4078 2009-05-25 19:02:18Z tack $
#
# This file contains a decorator usefull for functions that may need more
# time to execute and that needs more than one step to fullfill the task.
#
# A caller of a function decorated with 'coroutine' will either get the
# return value of the function call or an InProgress object in return. The
# first is similar to a normal function call, if an InProgress object is
# returned, this means that the function is still running. The object has a
# 'connect' function to connect a callback to get the results of the function
# call when it is done.
#
# A function decorated with 'coroutine' can't use 'return' to return the
# result of the function call. Instead it has to use yield to do this. Besides
# a normal return, the function can also return 'NotFinished' in the yield
# statement. In that case, the function call continues at this point in the
# next main loop iteration. If the function itself has to wait for a result of
# a function call (either another yield function are something else working
# async with an InProgress object) and it can create a 'InProgressCallback'
# object and use this as callback.
#
# The 'coroutine' decorator has a parameter interval. This is the
# interval used to schedule when the function should continue after a yield.
# The default value is 0, the first iteration is always called without a timer.
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

__all__ = [ 'NotFinished', 'coroutine' ]

# python imports
import sys
import logging

# kaa.base imports
from utils import property, wraps, DecoratorDataStore
from timer import Timer
from async import InProgress, InProgressAborted, InProgressStatus
from generator import generator

# get logging object
log = logging.getLogger('base')

# object to signal that the function whats to continue
NotFinished = object()

# Coroutine policy constants; see coroutine() for details.
POLICY_SYNCHRONIZED = 'synchronized'
POLICY_SINGLETON = 'singleton'
POLICY_PASS_LAST = 'passlast'

# Currently running (not stopped) CoroutineInProgress objects.  See
# CoroutineInProgress.__init__ for rational.
_active_coroutines = set()

def _process(generator, inprogress=None):
    """
    function to call next, step, or throw
    """
    if inprogress is not None:
        if inprogress._exception:
            inprogress._unhandled_exception = None
            return generator.throw(*inprogress._exception)
        return generator.send(inprogress._result)
    return generator.next()


def coroutine(interval=0, policy=None, progress=False, group=None):
    """
    Decorated functions (which must be generators) may yield control
    back to the mainloop and be subsequently resumed at a later time.

    Functions which yield ``kaa.NotFinished`` will be resumed on the
    next mainloop iteration; yielding an :class:`~kaa.InProgress` object
    will cause the coroutine to be resumed when the InProgress is finished.
    However, yielding a *finished* InProgress object will cause the coroutine
    to be resumed immediately.

    The coroutine is considered finished when the underlying generator yields
    a value other than ``kaa.NotFinished`` or an InProgress object.

    :param interval: Number of seconds to delay before resuming entry into
                     the coroutine.  Set to 0 (default) to resume as soon as
                     possible (but not sooner than the next mainloop iteration).
    :param policy: None, or one of ``POLICY_SYNCHRONIZED``, ``POLICY_SINGLETON``, or
                   ``POLICY_PASS_LAST`` (described below).
    :param progress: if True, a Progress object is passed as the first argument to
                     the decorated function, allowing the coroutine to report progress
                     to the caller.  (The progress parameter corresponds to the
                     ``progress`` attribute of the InProgress object returned to
                     the caller.)
    :param group: Name of the group this coroutine shares its policy with.  For
                  example, multiple coroutines with POLICY_SYNCHRONIZED and the
                  same group name will all be synchronized against each other.
    :return: an :class:`~kaa.InProgress` object representing the coroutine.

    Possible policies are:

        * ``kaa.POLICY_SYNCHRONIZED``: reentry into the coroutine is not permitted,
          and multiple calls are queued so that they execute sequentially.
        * ``kaa.POLICY_SINGLETON``: only one active instance of the coroutine is allowed
          to exist.  If the coroutine is invoked while another is running,
          the CoroutineInProgress object returned by the first invocation
          until it finishes.
        * ``kaa.POLICY_PASS_LAST``: passes the CoroutineInProgress of the most recently
          called, unfinished invocation of this coroutine as the 'last'
          kwarg.  If no such CoroutineInProgress exists, the last kwarg will
          be None.  This is useful to chain multiple invocations of the
          coroutine together, but unlike ``POLICY_SYNCHRONIZED``, the decorated
          function is entered each invocation.

    A function decorated with this decorator will always return an
    :class:`~kaa.InProgress` object. It may already be finished (which happens if
    the coroutine's first yielded value is one other than ``kaa.NotFinished`` or  
    an InProgress object).
    
    If it is not finished, the coroutine's life can be controlled via the
    :class:`~kaa.InProgress` it returns.  It can be :meth:`~kaa.InProgress.abort`ed,
    in which case a GeneratorExit will be raised inside the coroutine, or its
    interval may be adjusted via the :attr:`~kaa.CoroutineInProgress.interval` 
    property.
    """
    if progress is True:
        progress = InProgressStatus

    def decorator(func):
        @wraps(func, lshift=int(not not progress))
        def newfunc(*args, **kwargs):
            if policy:
                store = DecoratorDataStore(func, newfunc, args, group)
                if 'last' not in store:
                    store.last = []
                if 'lock' not in store:
                    store.lock = None
                last = store.last

                if policy == POLICY_SINGLETON and last:
                    # coroutine is still running, return original InProgress.
                    return last[-1]
                elif policy == POLICY_PASS_LAST:
                    if last:
                        kwargs['last'] = last[-1]
                    else:
                        kwargs['last'] = None

            def wrap(obj):
                """
                Finalizes the CoroutineInProgress return value for the
                coroutine.
                """
                if progress:
                    obj.progress = args[0]

                if policy in (POLICY_SINGLETON, POLICY_PASS_LAST) and not obj.finished:
                    last.append(obj)

                    # Attach a handler that removes the stored InProgress when it
                    # finishes.
                    def cb(*args, **kwargs):
                        last.remove(obj)
                        if args and args[0] in (GeneratorExit, InProgressAborted):
                            # Because we've attached to the exception signal
                            # we'll hear about GeneratorExit exceptions.
                            # Indicate those handled (by returning False) so as
                            # to suppress the unhandled async exception.
                            return False
                    obj.connect_both(cb)

                return obj


            func_info = (func.func_name, func.func_code.co_filename, func.func_code.co_firstlineno)
            if progress:
                args = (progress(),) + args
            result = func(*args, **kwargs)

            if not hasattr(result, 'next'):
                # Decorated function doesn't have a next attribute, which
                # means it isn't a generator.  We might simply wrap the result
                # in an InProgress and pass it back, but for example if the
                # coroutine is wrapping a @threaded decorated function which is
                # itself a generator, wrapping the result will silently not work
                # with any indication why.  It's better to raise an exception.
                raise ValueError('@coroutine decorated function is not a generator')

            function = result
            if policy == POLICY_SYNCHRONIZED and store.lock is not None and not store.lock.finished:
                # Function is currently called by someone else
                return wrap(CoroutineLockedInProgress(store, function, func_info, interval))

            ip = CoroutineInProgress(function, func_info, interval)
            if policy == POLICY_SYNCHRONIZED:
                store.lock = ip
            # Perform as much as we can of the coroutine now.
            if ip._step() == True:
                # Generator yielded NotFinished, so start the CoroutineInProgress timer.
                ip._timer.start(interval)
            return wrap(ip)


        # Boilerplate for @kaa.generator
        newfunc.decorator = coroutine
        newfunc.origfunc = func
        newfunc.redecorate = lambda: coroutine(interval, policy, progress)
        return newfunc

    return decorator

@generator.register(coroutine)
def _generator_coroutine(generator, func, args, kwargs):
    """
    kaa.generator support for kaa.coroutine
    """
    async = func(*args, **kwargs)
    while True:
        result = async.next()
        while isinstance(result, InProgress):
            try:
                result = async.send((yield result))
            except Exception, e:
                async.throw(*sys.exc_info())
        if result == NotFinished:
            yield result
        else:
            generator.send(result)


# -----------------------------------------------------------------------------
# Internal classes
# -----------------------------------------------------------------------------

class CoroutineInProgress(InProgress):
    """
    InProgress class that runs a generator function. This is also the return value
    for coroutine if it takes some more time. progress can be either NotFinished
    (iterate now) or InProgress (wait until InProgress is done).
    """
    def __init__(self, function, function_info, interval, progress=None):
        InProgress.__init__(self)
        self._coroutine = function
        self._coroutine_info = function_info
        self._timer = Timer(self._step)
        self._interval = interval
        self._prerequisite_ip = None
        self._valid = True

        # This object (self) represents a coroutine that is in progress: that
        # is, at some point in the coroutine, it has yielded and expects
        # to be reentered at some point.  Even if there are no outside
        # references to this CoroutineInProgress object, the coroutine must
        # resume.
        #
        # Here, an "outside reference" refers to a reference kept by the
        # caller of the API (that is, not refs kept by kaa internally).
        #
        # For other types of InProgress objects, when there are no outside
        # references to them, clearly nobody is interested in the result, so
        # they can be destroyed.  For CoroutineInProgress, we mustn't rely
        # on outside references to keep the coroutine alive, so we keep refs
        # for active CoroutineInProgress objects in a global set called
        # _active_coroutines.  We then then remove ourselves from this set when
        # stopped.
        #
        _active_coroutines.add(self)

        if progress is NotFinished:
            # coroutine was stopped NotFinished, start the step timer
            self._timer.start(interval)
        elif isinstance(progress, InProgress):
            # continue when InProgress is done
            self._prerequisite_ip = progress
            progress.connect_both(self._continue, self._continue)
        elif progress is not None:
            raise AttributeError('invalid progress %s' % progress)


    @property
    def interval(self):
        """
        The interval between the coroutine yielding a ``kaa.NotFinished`` or
        :class:`~kaa.InProgress` and reentry.
        """
        return self._interval

    @interval.setter  
    def interval(self, interval):
        if self._timer and self._timer.active:
            # restart timer
            self._timer.start(interval)
        self._interval = interval


    def _continue(self, *args, **kwargs):
        """
        Restart timer to call _step() after interval seconds.
        """
        if self._timer:
            self._timer.start(self._interval)


    def _step(self):
        """
        Call next step of the coroutine.
        """
        try:
            while True:
                result = _process(self._coroutine, self._prerequisite_ip)
                self._prerequisite_ip = None
                if result is NotFinished:
                    # Schedule next iteration with the timer
                    return True
                elif not isinstance(result, InProgress):
                    # Coroutine is done.
                    break

                # Result is an InProgress, so there's more work to do.
                self._prerequisite_ip = result
                if not result.finished:
                    # Coroutine yielded an unfinished InProgress, so continue
                    # when it is finished.
                    result.connect_both(self._continue, self._continue)
                    # Return False to stop the step timer.  It will be
                    # restarted when this newly returned InProgress is
                    # finished.
                    return False

                # If we're here, then the coroutine had yielded a finished
                # InProgress, so we can iterate immediately and step back
                # into the coroutine.

        except StopIteration:
            # Generator is exhausted but did not yield a result, so use None as
            # result.
            result = None
        except BaseException, e:
            # Generator raised an exception, so finish InProgress with that
            # exception.  We throw all exceptions, including SE and KI, in
            # case a thread is waiting on the InProgress.
            self.throw(*sys.exc_info())
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                # Reraise these signals back up the mainloop.
                raise
            return False

        # Coroutine is done, stop and finish with its result (which may be
        # None if no result was explicitly yielded).
        self._stop(finished=True)
        self.finish(result)
        return False


    def throw(self, *args):
        """
        Hook InProgress.throw to stop before finishing.  Allows a
        coroutine to be aborted asynchronously.
        """
        self._stop(finished=True)
        return super(CoroutineInProgress, self).throw(*args)


    def abort(self, exc=None):
        if isinstance(self._prerequisite_ip, InProgress):
            self._prerequisite_ip.disconnect(self._continue)
            self._prerequisite_ip.exception.disconnect(self._continue)

            # It's possible for _prerequisite_ip to exist and be finished
            # if this sequence occurs:
            #      1. IP finishes, and self._continue is called.
            #      2. Timer for self._continue is started.
            #      3. abort() is called before the mainloop fires the timer.
            # So we don't attempt to abort() it if it's already finished.
            if not self._prerequisite_ip.finished:
                try:
                    self._prerequisite_ip.abort(exc)
                except Exception:
                    log.exception('Error aborting %s yielded from coroutine', self._prerequisite_ip)

        if self._coroutine:
            return self._stop(exc=exc)


    def _stop(self, finished=False, exc=None):
        """
        Stop the function, no callbacks called.
        """
        if self._timer and self._timer.active:
            self._timer.stop()

        if self in _active_coroutines:
            _active_coroutines.remove(self)

        # if this object waits for another CoroutineInProgress, stop
        # that one, too.
        if isinstance(self._prerequisite_ip, InProgress):
            # Disconnect from the coroutine we're waiting on.  In case ours is
            # unfinished, we don't need to hear back about the GeneratorExit
            # exception we're about to throw it.
            self._prerequisite_ip.disconnect(self._continue)
            self._prerequisite_ip.exception.disconnect(self._continue)
            # Don't abort, because some other coroutine may be waiting on this one
            # too, and it would be rude of us to abort it just because we're no longer
            # interested.  (We do abort in CoroutineInProgress.abort() however.)
            ### self._prerequisite_ip.abort()

        try:
            if not finished:
                # Throw an InProgressAborted exception so that any callbacks
                # attached to us get notified that we've aborted.  The
                # generator itself will receive a GeneratorExit exception via
                # the generator's close() method later on.
                self.signals['abort'].emit(exc)
                if len(self.exception):
                    if not exc:
                        exc = InProgressAborted('Coroutine aborted')
                    super(CoroutineInProgress, self).throw(exc.__class__, exc, None)

            # This is a (potentially) active coroutine that expects to be reentered and we
            # are aborting it prematurely.  We call the generator's close() method
            # (introduced in Python 2.5), which raises GeneratorExit inside the coroutine
            # where it last yielded.  This allows the coroutine to perform any cleanup if
            # necessary.  New exceptions raised inside the coroutine are bubbled up
            # through close().
            #
            # Even if the generator has completed to termination (StopIteration) we can
            # safely call close(), and can even call it multiple times with no ill effect.
            # So we call it explicitly now and catch any 'generator ignored GeneratorExit'
            # exceptions it might raise so that we can log some more sensible output.
            try:
                self._coroutine.close()
            except RuntimeError:
                # "generator ignored GeneratorExit".  Log something useful.  This happens
                # when the generator catches GeneratorExit but doesn't reraise it (or
                # StopIteratorion).  See PEP 342.
                log.warning('Coroutine "%s" at %s:%s ignored GeneratorExit', *self._coroutine_info)
        finally:
            # Remove the internal timer, the async result and the
            # generator function to remove bad circular references.
            self._timer = None
            self._coroutine = None
            self._prerequisite_ip = None



class CoroutineLockedInProgress(CoroutineInProgress):
    """
    CoroutineInProgress for handling locked coroutine functions.
    """
    def __init__(self, store, function, function_info, interval):
        CoroutineInProgress.__init__(self, function, function_info, interval)
        self._store = store
        self._store.lock.connect_both(self._try_again, self._try_again)


    def _try_again(self, *args, **kwargs):
        """
        Try to start now.
        """
        if not self._store.lock.finished:
            # still locked by a new call, wait again
            self._store.lock.connect_both(self._try_again, self._try_again)
            return
        self._store.lock = self
        self._continue()
