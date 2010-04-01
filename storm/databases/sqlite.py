#
# Copyright (c) 2006, 2007 Canonical
#
# Written by Gustavo Niemeyer <gustavo@niemeyer.net>
#
# This file is part of Storm Object Relational Mapper.
#
# Storm is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Storm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from datetime import datetime, date, time, timedelta
from time import sleep, time as now
import sys

from storm.databases import dummy

try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    try:
        from sqlite3 import dbapi2 as sqlite
    except ImportError:
        sqlite = dummy

from storm.variables import Variable, RawStrVariable
from storm.database import Database, Connection, Result
from storm.exceptions import install_exceptions, DatabaseModuleError
from storm.expr import (
    Insert, Select, SELECT, Undef, SQLRaw, Union, Except, Intersect,
    compile, compile_insert, compile_select)


install_exceptions(sqlite)


compile = compile.create_child()

@compile.when(Select)
def compile_select_sqlite(compile, select, state):
    if select.offset is not Undef and select.limit is Undef:
        select.limit = sys.maxint
    statement = compile_select(compile, select, state)
    if state.context is SELECT:
        # SQLite breaks with (SELECT ...) UNION (SELECT ...), so we
        # do SELECT * FROM (SELECT ...) instead.  This is important
        # because SELECT ... UNION SELECT ... ORDER BY binds the ORDER BY
        # to the UNION instead of SELECT.
        return "SELECT * FROM (%s)" % statement
    return statement

# Considering the above, selects have a greater precedence.
compile.set_precedence(5, Union, Except, Intersect)

@compile.when(Insert)
def compile_insert_sqlite(compile, insert, state):
    # SQLite fails with INSERT INTO table VALUES (), so we transform
    # that to INSERT INTO table (id) VALUES (NULL).
    if not insert.map and insert.primary_columns is not Undef:
        insert.map.update(dict.fromkeys(insert.primary_columns, None))
    return compile_insert(compile, insert, state)


class SQLiteResult(Result):

    def get_insert_identity(self, primary_key, primary_variables):
        return SQLRaw("(OID=%d)" % self._raw_cursor.lastrowid)

    @staticmethod
    def set_variable(variable, value):
        if isinstance(variable, RawStrVariable):
            # pysqlite2 may return unicode.
            value = str(value)
        variable.set(value, from_db=True)

    @staticmethod
    def from_database(row):
        """Convert MySQL-specific datatypes to "normal" Python types.

        If there are anny C{buffer} instances in the row, convert them
        to strings.
        """
        for value in row:
            if isinstance(value, buffer):
                yield str(value)
            else:
                yield value


class SQLiteConnection(Connection):

    result_factory = SQLiteResult
    compile = compile
    _in_transaction = False

    @staticmethod
    def to_database(params):
        """
        Like L{Connection.to_database}, but this also converts
        instances of L{datetime} types to strings, and strings
        instances to C{buffer} instances.
        """
        for param in params:
            if isinstance(param, Variable):
                param = param.get(to_db=True)
            if isinstance(param, (datetime, date, time, timedelta)):
                yield str(param)
            elif isinstance(param, str):
                yield buffer(param)
            else:
                yield param

    def commit(self):
        # See story at the end to understand why we do COMMIT manually.
        if self._in_transaction:
            self.raw_execute("COMMIT", _end=True)

    def rollback(self):
        # See story at the end to understand why we do ROLLBACK manually.
        if self._in_transaction:
            self.raw_execute("ROLLBACK", _end=True)

    def raw_execute(self, statement, params=None, _end=False):
        """Execute a raw statement with the given parameters.

        This method will automatically retry on locked database errors.
        This should be done by pysqlite, but it doesn't work with
        versions < 2.3.4, so we make sure the timeout is respected
        here.
        """
        if _end:
            self._in_transaction = False
        elif not self._in_transaction:
            # See story at the end to understand why we do BEGIN manually.
            self._in_transaction = True
            self._raw_connection.execute("BEGIN")

        # Remember the time at which we started the operation.  If pysqlite
        # handles the timeout correctly, we won't retry the operation, because
        # the timeout will have expired when the raw_execute() returns.
        started = now()
        while True:
            try:
                return Connection.raw_execute(self, statement, params)
            except sqlite.OperationalError, e:
                if str(e) != "database is locked":
                    raise
                elif now() - started < self._database._timeout:
                    # pysqlite didn't handle the timeout correctly,
                    # so we sleep a little and then retry.
                    sleep(0.1)
                else:
                    # The operation failed due to being unable to get a
                    # lock on the database.  In this case, we are still
                    # in a transaction.
                    if _end:
                        self._in_transaction = True
                    raise


class SQLite(Database):

    connection_factory = SQLiteConnection

    def __init__(self, uri):
        if sqlite is dummy:
            raise DatabaseModuleError("'pysqlite2' module not found")
        self._filename = uri.database or ":memory:"
        self._timeout = float(uri.options.get("timeout", 5))
        self._synchronous = uri.options.get("synchronous")

    def raw_connect(self):
        # See the story at the end to understand why we set isolation_level.
        raw_connection = sqlite.connect(self._filename, timeout=self._timeout,
                                        isolation_level=None)
        if self._synchronous is not None:
            raw_connection.execute("PRAGMA synchronous = %s" %
                                   (self._synchronous,))
        return raw_connection


create_from_uri = SQLite


# Here is a sad story about PySQLite2.
# 
# PySQLite does some very dirty tricks to control the moment in
# which transactions begin and end.  It actually *changes* the
# transactional behavior of SQLite.
# 
# The real behavior of SQLite is that transactions are SERIALIZABLE
# by default.  That is, any reads are repeatable, and changes in
# other threads or processes won't modify data for already started
# transactions that have issued any reading or writing statements.
# 
# PySQLite changes that in a very unpredictable way.  First, it will
# only actually begin a transaction if a INSERT/UPDATE/DELETE/REPLACE
# operation is executed (yes, it will parse the statement).  This
# means that any SELECTs executed *before* one of the former mentioned
# operations are seen, will be operating in READ COMMITTED mode.  Then,
# if after that a INSERT/UPDATE/DELETE/REPLACE is seen, the transaction
# actually begins, and so it moves into SERIALIZABLE mode.
# 
# Another pretty surprising behavior is that it will *commit* any
# on-going transaction if any other statement besides
# SELECT/INSERT/UPDATE/DELETE/REPLACE is seen.
# 
# In an ORM we're really dealing with cached data, so working on top
# of a system like that means that cache validity is pretty random.
# 
# So what we do about that in this module is disabling all that hackery
# by *pretending* to PySQLite that we'll work without transactions
# (isolation_level=None), and then we actually take responsibility for
# controlling the transaction.
# 
# References:
#     http://www.sqlite.org/lockingv3.html
#     http://docs.python.org/lib/sqlite3-Controlling-Transactions.html
#
