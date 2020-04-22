# Copyright REFITT Team 2019. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""Access and management to REFITT's database."""

# type annotations
from typing import List, Dict, Any

# standard libs
import functools

# internal libs
from . import config
from . import client as client_
from .client import DatabaseClient
from refitt.core.logging import Logger

# external libs
from pandas import DataFrame, read_sql
from sqlalchemy.sql import text
from sqlalchemy.engine.result import ResultProxy


# initialize module level logger
log = Logger.with_name('refitt.database')


def execute(statement: str, client: DatabaseClient = None, **params) -> ResultProxy:
    """
    Execute arbitrary SQL `statement`.

    Arguments
    ---------
    statement: str
        An SQL query to execute.

    client: `refitt.database.core.client.DatabaseClient`
        A client connection to the database. If None, one will either be created temporarily
        for the lifetime of this query, or if a `refitt.database.core.client._PERSISTENT_CLIENT`
        exists, it will be used.

    Returns
    -------
    result: `sqlalchemy.engine.result.ResultProxy`

    See Also
    --------
    - `sqlalchemy.engine.execute`

    Example
    -------
    >>> from refitt import database
    >>> database.execute('select * from observation.object_type limit 2').fetchall()
    [(1, 'SNIa', 'WD detonation, Type Ia SN'),
     (2, 'SNIa-91bg', 'Peculiar type Ia: 91bg')]
    """
    if client is not None:
        return client.engine.execute(text(statement), **params)
    if client_._PERSISTENT_CLIENT is not None:  # noqa
        return client_._PERSISTENT_CLIENT.engine.execute(text(statement), **params)  # noqa
    with DatabaseClient.from_config() as client:
        return client.engine.execute(text(statement), **params)


def insert(data: DataFrame, schema: str, table: str, client: DatabaseClient = None,
           if_exists: str = 'append', index: bool = False, chunksize: int = 10_000) -> None:
    """
    Insert `data` into `schema`.`table`.

    Arguments
    ---------
    data: `pandas.DataFrame`
        The data to be inserted into the database.

    schema: str
        The name of the schema for the `table`.

    table: str
        The name of the table to insert into.

    client: `refitt.database.core.client.DatabaseClient`
        A client connection to the database. If None, one will either be created temporarily
        for the lifetime of this query, or if a `refitt.database.core.client._PERSISTENT_CLIENT`
        exists, it will be used.

    if_exists: str (default: 'append')
        Action to take if the `table` already exists. (see `pandas.DataFrame.to_sql`).

    index: bool (default: False)
        Whether to include the index for insertion. (see `pandas.DataFrame.to_sql`).

    chunksize: int (default: 10_000)
        Number of rows to insert at a time. (see `pandas.DataFrame.to_sql`).

    See Also
    --------
    - `pandas.DataFrame.to_sql`
    """
    if client is not None:
        return data.to_sql(table, client.engine, schema=schema, if_exists=if_exists,
                           index=index, chunksize=chunksize)
    if client_._PERSISTENT_CLIENT is not None:
        return data.to_sql(table, client_._PERSISTENT_CLIENT.engine, schema=schema,
                           if_exists=if_exists, index=index, chunksize=chunksize)
    with DatabaseClient.from_config() as client:
        return data.to_sql(table, client.engine, schema=schema, if_exists=if_exists,
                           index=index, chunksize=chunksize)


def _select(query: str, client: DatabaseClient = None, **params) -> DataFrame:
    """
    Execute SQL `query` statement.

    Arguments
    ---------
    query: str
        The SQL query to submit to the database.

    client: `refitt.database.client.DatabaseClient`
        A client connection to the database. If None, one will either
        be created temporarily for the lifetime of this query, or if a
        `refitt.database.client._PERSISTENT_CLIENT` exists, it will be used.

    Returns
    -------
    table: `pandas.DataFrame`

    See Also
    --------
    - `refitt.database.interface.select`
    - `pandas.read_sql`
    """
    if client is not None:
        return read_sql(text(query), client.engine, params=params)
    if client_._PERSISTENT_CLIENT is not None:  # noqa
        return read_sql(text(query), client_._PERSISTENT_CLIENT.engine, params=params)  # noqa
    with DatabaseClient.from_config() as client:
        return read_sql(text(query), client.engine, params=params)


_FIND_COLUMNS = """\
SELECT column_name FROM information_schema.columns
WHERE table_schema = :schema AND table_name = :table
"""


@functools.lru_cache(maxsize=None)
def get_columns(schema: str, table: str) -> List[str]:
    """List of column names."""
    columns = _select(_FIND_COLUMNS, schema=schema, table=table)
    return columns.loc[:, 'column_name'].to_list()


_FIND_TABLES = """\
SELECT table_name from information_schema.tables 
WHERE table_schema = :schema
"""


@functools.lru_cache(maxsize=None)
def get_tables(schema: str) -> List[str]:
    """List of member tables."""
    tables = _select(_FIND_TABLES, schema=schema)
    return tables.loc[:, 'table_name'].to_list()


_FIND_FOREIGN_KEYS = """\
SELECT
    table_constraints.table_schema       AS table_schema,
    table_constraints.constraint_name    AS constraint_name,
    table_constraints.table_name         AS table_name,
    key_column_usage.column_name         AS column_name,
    constraint_column_usage.table_schema AS foreign_table_schema,
    constraint_column_usage.table_name   AS foreign_table_name,
    constraint_column_usage.column_name  AS foreign_column_name

FROM
    information_schema.table_constraints

JOIN
    information_schema.key_column_usage
    ON
        table_constraints.constraint_name = key_column_usage.constraint_name AND
        table_constraints.table_schema = key_column_usage.table_schema

JOIN
    information_schema.constraint_column_usage
    ON
        constraint_column_usage.constraint_name = table_constraints.constraint_name AND
        constraint_column_usage.table_schema = table_constraints.table_schema

WHERE
    table_constraints.constraint_type = 'FOREIGN KEY' AND
    table_constraints.table_schema = :schema AND
    table_constraints.table_name = :table;
"""


_SELECT_TEMPLATE = """\
SELECT
    {columns}

FROM
    "{schema}"."{table}"
"""


_JOIN_TEMPLATE = """
JOIN
    "{foreign_schema}"."{foreign_table}"
    ON
        "{table}"."{column}" = "{foreign_table}"."{foreign_column}"
"""


def _make_select(columns: List[str], schema: str, table: str, where: List[str] = None,
                 limit: int = None, orderby: str = None, ascending: bool = True,
                 join: bool = False) -> str:
    """Build SQL query. See also: `select`."""

    if not columns:
        columns = get_columns(schema, table)

    columns = ', \n    '.join([f'"{table}"."{name}"' for name in columns])
    query = _SELECT_TEMPLATE.format(columns=columns, schema=schema, table=table)

    if join:
        fkeys = _select(_FIND_FOREIGN_KEYS, schema=schema, table=table).drop_duplicates()
        for _, fkey in fkeys.iterrows():
            foreign_table_columns = get_columns(fkey.foreign_table_schema, fkey.foreign_table_name)
            alternate = fkey.foreign_column_name.replace('_id', '_name')
            if alternate in foreign_table_columns:
                query = query.replace(f'"{table}"."{fkey.column_name}"',
                                      f'"{fkey.foreign_table_name}"."{alternate}" AS "{alternate}"')
                query = query + _JOIN_TEMPLATE.format(foreign_schema=fkey.foreign_table_schema,
                                                      foreign_table=fkey.foreign_table_name,
                                                      foreign_column=fkey.foreign_column_name,
                                                      table=fkey.table_name,
                                                      column=fkey.column_name)
    if where:
        query += '\nWHERE\n    ' + '\n    AND '.join(where)

    if orderby is not None:
        query += f'\nORDER BY "{table}"."{orderby}"'
        query += ' ASC' if ascending else ' DESC'

    if limit is not None:
        query += f'\nLIMIT {int(limit)}\n'

    return query


def select(columns: List[str], schema: str, table: str, client: DatabaseClient = None,
           where: List[str] = None, limit: int = None, orderby: str = None, ascending: bool = True,
           join: bool = False, set_index: bool = True) -> DataFrame:
    """
    Construct an SQL query and execute.

    Arguments
    ---------

    Returns
    -------
    table: `pandas.DataFrame`
    """
    query = _make_select(columns, schema, table, where=where, limit=limit,
                         orderby=orderby, ascending=ascending, join=join)
    result = _select(query, client)
    if set_index is True and f'{table}_id' in result.columns:
        result = result.set_index(f'{table}_id')
    return result


class Table:
    """Generic interface to database table."""

    schema: str = None
    name: str = None

    def __init__(self, schema: str, name: str) -> None:
        """Initialize with fully qualified name."""
        self.schema = schema
        self.name = name

    @property
    def columns(self) -> List[str]:
        """List of column names."""
        return get_columns(self.schema, self.name)

    def select(self, columns: List[str] = None, **options) -> DataFrame:
        """Select records from the table."""
        return select(columns, self.schema, self.name, **options)

    def insert(self, dataframe: DataFrame, **options) -> None:
        """Insert full `dataframe` into table."""
        insert(dataframe, self.schema, self.name, **options)

    def insert_record(self, record: Dict[str, Any]) -> None:
        """Insert named `fields` into the table."""
        table_slice = DataFrame({field: [value] for field, value in record.items()})
        self.insert(table_slice)

    def __str__(self) -> str:
        """String view of table interface."""
        return f'<{self.__class__.__name__}({self.schema}.{self.name})>'

    def __repr__(self) -> str:
        """Interactive representation of table interface."""
        return str(self)