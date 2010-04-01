from datetime import datetime
import sys

from storm.exceptions import TimeoutError
from storm.expr import Variable


class DebugTracer(object):

    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stderr
        self._stream = stream

    def connection_raw_execute(self, connection, raw_cursor, statement, params):
        time = datetime.now().isoformat()[11:]
        raw_params = []
        for param in params:
            if isinstance(param, Variable):
                raw_params.append(param.get())
            else:
                raw_params.append(param)
        raw_params = tuple(raw_params)
        self._stream.write(
            "[%s] EXECUTE: %r, %r\n" % (time, statement, raw_params))
        self._stream.flush()

    def connection_raw_execute_error(self, connection, raw_cursor,
                                     statement, params, error):
        time = datetime.now().isoformat()[11:]
        self._stream.write("[%s] ERROR: %s\n" % (time, error))
        self._stream.flush()

    def connection_raw_execute_success(self, connection, raw_cursor,
                                       statement, params):
        time = datetime.now().isoformat()[11:]
        self._stream.write("[%s] DONE\n" % time)
        self._stream.flush()


class TimeoutTracer(object):

    def __init__(self, granularity=5):
        self.granularity = granularity

    def connection_raw_execute(self, connection, raw_cursor, statement, params):
        remaining_time = self.get_remaining_time()
        if remaining_time <= 0:
            raise TimeoutError(statement, params)

        last_remaining_time = getattr(connection,
                                      "_timeout_tracer_remaining_time", 0)
        if (remaining_time > last_remaining_time or
            last_remaining_time - remaining_time >= self.granularity):
            self.set_statement_timeout(raw_cursor, remaining_time)
            connection._timeout_tracer_remaining_time = remaining_time

    def connection_raw_execute_error(self, connection, raw_cursor,
                                     statement, params, error):
        """Raise TimeoutError if the given error was a timeout issue.

        Must be specialized in the backend.
        """
        raise NotImplementedError("%s.connection_raw_execute_error() must be "
                                  "implemented" % self.__class__.__name__)

    def set_statement_timeout(self, raw_cursor, remaining_time):
        """Perform the timeout setup in the raw cursor.

        The database should raise an error if the next statement takes
        more than the number of seconds provided in C{remaining_time}.

        Must be specialized in the backend.
        """
        raise NotImplementedError("%s.set_statement_timeout() must be "
                                  "implemented" % self.__class__.__name__)

    def get_remaining_time(self):
        """Tells how much time the current context (HTTP request, etc) has.

        Must be specialized with application logic.

        @return: Number of seconds allowed for the next statement.
        """
        raise NotImplementedError("%s.get_remaining_time() must be implemented"
                                  % self.__class__.__name__)


_tracers = []

def trace(name, *args, **kwargs):
    for tracer in _tracers:
        attr = getattr(tracer, name, None)
        if attr:
            attr(*args, **kwargs)

def install_tracer(tracer):
    _tracers.append(tracer)

def get_tracers():
    return _tracers[:]

def remove_all_tracers():
    del _tracers[:]

def remove_tracer_type(tracer_type):
    for i in range(len(_tracers)-1, -1, -1):
        if type(_tracers[i]) is tracer_type:
            del _tracers[i]

def debug(flag, stream=None):
    remove_tracer_type(DebugTracer)
    if flag:
        install_tracer(DebugTracer(stream=stream))
