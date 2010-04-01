#
# Copyright (c) 2006-2009 Canonical
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
from distutils.version import LooseVersion

from storm.databases import dummy

# PostgreSQL support in Storm requires psycopg2 2.0.7 or greater.
# Earlier versions of psyocpg2 contain data loss bugs.
# See https://bugs.launchpad.net/storm/+bug/322206 for more details.
REQUIRED_PSYCOPG2_VERSION = LooseVersion('2.0.7')
PSYCOPG2_VERSION = None
try:
    import psycopg2
    PSYCOPG2_VERSION = LooseVersion(psycopg2.__version__.split(' ')[0])
    if PSYCOPG2_VERSION < REQUIRED_PSYCOPG2_VERSION:
        psycopg2 = dummy
    else:
        import psycopg2.extensions
except ImportError:
    psycopg2 = dummy

from storm.expr import (
    Undef, Expr, SetExpr, Select, Insert, Alias, And, Eq, FuncExpr, SQLRaw,
    Sequence, Like, SQLToken, COLUMN, COLUMN_NAME, COLUMN_PREFIX, TABLE,
    compile, compile_select, compile_insert, compile_set_expr, compile_like,
    compile_sql_token)
from storm.variables import Variable, ListVariable
from storm.database import Database, Connection, Result
from storm.exceptions import (
    install_exceptions, DatabaseError, DatabaseModuleError, InterfaceError,
    OperationalError, ProgrammingError, TimeoutError)
from storm.tracer import TimeoutTracer


install_exceptions(psycopg2)
compile = compile.create_child()


class Returning(Expr):
    """Appends the "RETURNING <primary_columns>" suffix to an INSERT.

    This is only supported in PostgreSQL 8.2+.
    """

    def __init__(self, insert):
        self.insert = insert

@compile.when(Returning)
def compile_returning(compile, expr, state):
    state.push("context", COLUMN)
    columns = compile(expr.insert.primary_columns, state)
    state.pop()
    state.push("precedence", 0)
    insert = compile(expr.insert, state)
    state.pop()
    return "%s RETURNING %s" % (insert, columns)


class currval(FuncExpr):

    name = "currval"

    def __init__(self, column):
        self.column = column

@compile.when(currval)
def compile_currval(compile, expr, state):
    """Compile a currval.

    This is a bit involved because we have to get escaping right.  Here
    are a few cases to keep in mind::

        currval('thetable_thecolumn_seq')
        currval('theschema.thetable_thecolumn_seq')
        currval('"the schema".thetable_thecolumn_seq')
        currval('theschema."the table_thecolumn_seq"')
        currval('theschema."thetable_the column_seq"')
        currval('"thetable_the column_seq"')
        currval('"the schema"."the table_the column_seq"')

    """
    state.push("context", COLUMN_PREFIX)
    table = compile(expr.column.table, state, token=True)
    state.pop()
    column_name = compile(expr.column.name, state, token=True)
    if table.endswith('"'):
        table = table[:-1]
        if column_name.endswith('"'):
            column_name = column_name[1:-1]
        return "currval('%s_%s_seq\"')" % (table, column_name)
    elif column_name.endswith('"'):
        column_name = column_name[1:-1]
        if "." in table:
            schema, table = table.rsplit(".", 1)
            return "currval('%s.\"%s_%s_seq\"')" % (schema, table, column_name)
        else:
            return "currval('\"%s_%s_seq\"')" % (table, column_name)
    else:
        return "currval('%s_%s_seq')" % (table, column_name)


@compile.when(ListVariable)
def compile_list_variable(compile, list_variable, state):
    elements = []
    variables = list_variable.get(to_db=True)
    if variables is None:
        return "NULL"
    if not variables:
        return "'{}'"
    for variable in variables:
        elements.append(compile(variable, state))
    return "ARRAY[%s]" % ",".join(elements)


@compile.when(SetExpr)
def compile_set_expr_postgres(compile, expr, state):
    if expr.order_by is not Undef:
        # The following statement breaks in postgres:
        #     SELECT 1 AS id UNION SELECT 1 ORDER BY id+1
        # With the error:
        #     ORDER BY on a UNION/INTERSECT/EXCEPT result must
        #     be on one of the result columns
        # So we transform it into something close to:
        #     SELECT * FROM (SELECT 1 AS id UNION SELECT 1) AS a ORDER BY id+1

        # Build new set expression without arguments (order_by, etc).
        new_expr = expr.__class__()
        new_expr.exprs = expr.exprs
        new_expr.all = expr.all

        # Make sure that state.aliases isn't None, since we want them to
        # compile our order_by statement below.
        no_aliases = state.aliases is None
        if no_aliases:
            state.push("aliases", {})

        # Build set expression, collecting aliases.
        set_stmt = SQLRaw("(%s)" % compile_set_expr(compile, new_expr, state))

        # Build order_by statement, using aliases.
        state.push("context", COLUMN_NAME)
        order_by_stmt = SQLRaw(compile(expr.order_by, state))
        state.pop()

        # Discard aliases, if they were not being collected previously.
        if no_aliases:
            state.pop()

        # Build wrapping select statement.
        select = Select(SQLRaw("*"), tables=Alias(set_stmt), limit=expr.limit,
                        offset=expr.offset, order_by=order_by_stmt)
        return compile_select(compile, select, state)
    else:
        return compile_set_expr(compile, expr, state)


@compile.when(Insert)
def compile_insert_postgres(compile, insert, state):
    # PostgreSQL fails with INSERT INTO table VALUES (), so we transform
    # that to INSERT INTO table (id) VALUES (DEFAULT).
    if not insert.map and insert.primary_columns is not Undef:
        insert.map.update(dict.fromkeys(insert.primary_columns,
                                        SQLRaw("DEFAULT")))
    return compile_insert(compile, insert, state)


@compile.when(Sequence)
def compile_sequence_postgres(compile, sequence, state):
    return "nextval('%s')" % sequence.name


@compile.when(Like)
def compile_like_postgres(compile, like, state):
    if like.case_sensitive is False:
        return compile_like(compile, like, state, oper=" ILIKE ")
    return compile_like(compile, like, state)


@compile.when(SQLToken)
def compile_sql_token_postgres(compile, expr, state):
    if "." in expr and state.context in (TABLE, COLUMN_PREFIX):
        return ".".join(compile_sql_token(compile, subexpr, state)
                        for subexpr in expr.split("."))
    return compile_sql_token(compile, expr, state)


class PostgresResult(Result):

    def get_insert_identity(self, primary_key, primary_variables):
        equals = []
        for column, variable in zip(primary_key, primary_variables):
            if not variable.is_defined():
                # The Select here prevents PostgreSQL from going nuts and
                # performing a sequential scan when there *is* an index.
                # http://tinyurl.com/2n8mv3
                variable = Select(currval(column))
            equals.append(Eq(column, variable))
        return And(*equals)


class PostgresConnection(Connection):

    result_factory = PostgresResult
    param_mark = "%s"
    compile = compile

    def execute(self, statement, params=None, noresult=False):
        """Execute a statement with the given parameters.

        This extends the L{Connection.execute} method to add support
        for automatic retrieval of inserted primary keys to link
        in-memory objects with their specific rows.
        """
        if (isinstance(statement, Insert) and
            self._database._version >= 80200 and
            statement.primary_variables is not Undef and
            statement.primary_columns is not Undef):

            # Here we decorate the Insert statement with a Returning
            # expression, so that we get back in the result the values
            # for the primary key just inserted.  This prevents a round
            # trip to the database for obtaining these values.

            result = Connection.execute(self, Returning(statement), params)
            for variable, value in zip(statement.primary_variables,
                                       result.get_one()):
                result.set_variable(variable, value)
            return result

        return Connection.execute(self, statement, params, noresult)

    def raw_execute(self, statement, params):
        """
        Like L{Connection.raw_execute}, but encode the statement to
        UTF-8 if it is unicode.
        """
        if type(statement) is unicode:
            # psycopg breaks with unicode statements.
            statement = statement.encode("UTF-8")
        return Connection.raw_execute(self, statement, params)

    def to_database(self, params):
        """
        Like L{Connection.to_database}, but this converts datetime
        types to strings, unicode to UTF-8 encoded strings, and
        strings to L{psycopg2.Binary} instances.
        """
        for param in params:
            if isinstance(param, Variable):
                param = param.get(to_db=True)
            if isinstance(param, (datetime, date, time, timedelta)):
                yield str(param)
            elif isinstance(param, unicode):
                yield param.encode("UTF-8")
            elif isinstance(param, str):
                yield psycopg2.Binary(param)
            else:
                yield param

    def is_disconnection_error(self, exc):
        if not isinstance(exc, (InterfaceError, OperationalError,
                                ProgrammingError)):
            return False

        # XXX: 2007-09-17 jamesh
        # The last message is for the benefit of old versions of
        # psycopg2 (prior to 2.0.7) which have a bug related to
        # stripping the error severity from the message.
        msg = str(exc)
        return ("server closed the connection unexpectedly" in msg or
                "could not connect to server" in msg or
                "no connection to the server" in msg or
                "connection not open" in msg or
                "connection already closed" in msg or
                "losed the connection unexpectedly" in msg)


class Postgres(Database):

    connection_factory = PostgresConnection

    # An integer representing the server version.  If the server does
    # not support the server_version_num variable, this will be set to
    # 0.  In practice, this means the variable will be 0 or greater
    # than or equal to 80200.
    _version = None

    def __init__(self, uri):
        if psycopg2 is dummy:
            raise DatabaseModuleError(
                "'psycopg2' >= %s not found. Found %s."
                % (REQUIRED_PSYCOPG2_VERSION, PSYCOPG2_VERSION))
        self._dsn = make_dsn(uri)
        isolation = uri.options.get("isolation", "serializable")
        isolation_mapping = {
            "autocommit": psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT,
            "serializable": psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE,
            "read-committed": psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED,
        }
        try:
            self._isolation = isolation_mapping[isolation]
        except KeyError:
            raise ValueError(
                "Unknown serialization level %r: expected one of "
                "'autocommit', 'serializable', 'read-committed'" %
                (isolation,))

    def raw_connect(self):
        raw_connection = psycopg2.connect(self._dsn)

        if self._version is None:
            cursor = raw_connection.cursor()

            try:
                cursor.execute("SHOW server_version_num")
            except psycopg2.ProgrammingError:
                self._version = 0
            else:
                self._version = int(cursor.fetchone()[0])
            raw_connection.rollback()

        raw_connection.set_client_encoding("UTF8")
        raw_connection.set_isolation_level(self._isolation)
        return raw_connection


create_from_uri = Postgres


if psycopg2 is not dummy:
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2._psycopg.UNICODEARRAY)


def make_dsn(uri):
    """Convert a URI object to a PostgreSQL DSN string."""
    dsn = "dbname=%s" % uri.database
    if uri.host is not None:
        dsn += " host=%s" % uri.host
    if uri.port is not None:
        dsn += " port=%d" % uri.port
    if uri.username is not None:
        dsn += " user=%s" % uri.username
    if uri.password is not None:
        dsn += " password=%s" % uri.password
    return dsn


class PostgresTimeoutTracer(TimeoutTracer):

    def set_statement_timeout(self, raw_cursor, remaining_time):
        raw_cursor.execute("SET statement_timeout TO %d" %
                           (remaining_time * 1000))

    def connection_raw_execute_error(self, connection, raw_cursor,
                                     statement, params, error):
        # This should just check for
        # psycopg2.extensions.QueryCanceledError in the future.
        if (isinstance(error, DatabaseError) and
            "statement timeout" in str(error)):
            raise TimeoutError(statement, params)
