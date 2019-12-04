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

# standard libs
import os
import secrets
import functools

# type annotations
from typing import Tuple, Dict, Any, List

# internal libs
from ..core.logging import logger
from .client import DatabaseClient, ServerAddress, UserAuth
from .config import connection_info

# external libs
from pandas import DataFrame, read_sql
from sqlalchemy.engine.result import ResultProxy


# initialize module level logger
log = logger.with_name(f'refitt.database')


def execute(statement: str, **params) -> ResultProxy:
    """
    Execute arbitrary SQL `statement`.
    """
    info = connection_info()
    if 'tunnel' not in info:
        with DatabaseClient(**info['server']) as client:
            return client.engine.execute(statement, **params)
    else:
        with DatabaseClient(**info['server']).use_tunnel(**info['tunnel']) as client:
            return client.engine.execute(statement, **params)


def insert(data: DataFrame, table: str, schema: str, if_exists: str = 'append',
           index: bool = False, chunksize: int = 10000) -> None:
    """
    Insert `data` into `schema`.`table`.

    See Also:
        `pandas.DataFrame.to_sql`
    """
    info = connection_info()
    if 'tunnel' not in info:
        with DatabaseClient(**info['server']) as client:
            data.to_sql(table, client.engine, schema=schema, if_exists=if_exists, 
                        index=False, chunksize=chunksize)
    else:
        with DatabaseClient(**info['server']).use_tunnel(**info['tunnel']) as client:
            data.to_sql(table, client.engine, schema=schema, if_exists=if_exists, 
                        index=index, chunksize=chunksize)


def _select(query: str) -> DataFrame:
    """
    Execute SQL `query` statement.

    See Also:
        `pandas.read_sql`
    """
    info = connection_info()
    if 'tunnel' not in info:
        with DatabaseClient(**info['server']) as client:
            return read_sql(query, client.engine)
    else:
        with DatabaseClient(**info['server']).use_tunnel(**info['tunnel']) as client:
            return read_sql(query, client.engine)


def get_columns(schema: str, name: str) -> List[str]:
    """List of column names."""
    return list(_select(f"select column_name from information_schema.columns where "
                        f"table_schema = '{schema}' and table_name = '{name}'")['column_name'])


def get_tables(schema: str) -> List[str]:
    """List of member tables."""
    return list(_select(f"select table_name from information_schema.tables where "
                        f"table_schema = '{schema}'")['table_name'])


FOREIGN_KEY_QUERY = """\
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
    table_constraints.table_schema='{schema}' AND
    table_constraints.table_name='{table}';
"""


SELECT_TEMPLATE = """\
SELECT
    {columns}

FROM
    "{schema}"."{table}"
"""


JOIN_TEMPLATE = """
JOIN
    "{foreign_schema}"."{foreign_table}"
    ON
        "{table}"."{column}" = "{foreign_table}"."{foreign_column}"
"""


def _make_select(columns: List[str], schema: str, table: str, where: List[str] = [],
                 limit: int = None, orderby: str = None, ascending: bool = True,
                 join: bool = False) -> str:
    """Build SQL query. See also: `select`."""
    
    if not columns:
        columns = get_columns(schema, table)

    columns = ', \n    '.join([f'"{table}"."{name}"' for name in columns])
    query = SELECT_TEMPLATE.format(columns=columns, schema=schema, table=table)

    if join:
        fkeys = _select(FOREIGN_KEY_QUERY.format(schema=schema, table=table)).drop_duplicates()
        for _, fkey in fkeys.iterrows():
            foreign_table_columns = get_columns(fkey.foreign_table_schema, fkey.foreign_table_name)
            alternate = fkey.foreign_column_name.replace('_id', '_name')
            if alternate in foreign_table_columns:
                query = query.replace(f'"{table}"."{fkey.column_name}"',
                                      f'"{fkey.foreign_table_name}"."{alternate}" AS "{alternate}"')
                query = query + JOIN_TEMPLATE.format(foreign_schema=fkey.foreign_table_schema,
                                                     foreign_table=fkey.foreign_table_name,
                                                     foreign_column=fkey.foreign_column_name,
                                                     table=fkey.table_name,
                                                     column=fkey.column_name)

    if where:
        query += '\nWHERE\n    ' + '\n    AND '.join(where)

    if orderby is not None:
        query += f'\nORDER BY "{orderby}"'
        query += ' ASC' if ascending else ' DESC'

    if limit is not None:
        query += f'\nLIMIT {int(limit)}\n'

    return query


def select(columns: List[str], schema: str, table: str, where: List[str] = [],
           limit: int = None, orderby: str = None, ascending: bool = True, 
           join: bool = False, set_index: bool = True) -> DataFrame:
    """
    Construct an SQL query and execute.

    Arguments
    ---------

    Returns
    -------
    result: `pandas.DataFrame`
        The resulting table from the query.
    """

    query = _make_select(columns, schema, table, where=where, limit=limit, 
                         orderby=orderby, ascending=ascending, join=join)
    result = _select(query)
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
    @functools.lru_cache(maxsize=1)
    def columns(self) -> List[str]:
        """List of column names."""
        return get_columns(self.schema, self.name)
    
    def select(self, columns: List[str] = [], **options) -> DataFrame:
        """Select records from the table."""
        return select(columns, self.schema, self.name, **options)
    
    def insert(self, dataframe: DataFrame, **options) -> None:
        """Insert full `dataframe` into table."""
        insert(dataframe, self.name, self.schema, **options)

    def insert_record(self, **fields) -> None:
        """Insert named `fields` into the table."""
        table_slice = DataFrame({field: [value] for field, value in fields.items()})
        self.insert(table_slice)

    def __str__(self) -> str:
        """String view of table interface."""
        return f'<{self.__class__.__name__}({self.schema}.{self.name})>'
    
    def __repr__(self) -> str:
        """Interactive representation of table interface."""
        return str(self)


class Schema:
    """Generic interface to database schema."""

    name: str = None

    def __init__(self, name: str) -> None:
        self.name = name
    
    @property
    @functools.lru_cache(maxsize=1)
    def tables(self) -> List[str]:
        """List of member tables."""
        return get_tables(self.name)
    
    @functools.lru_cache(maxsize=None)
    def __getitem__(self, table: str) -> Table:
        """Get table interface."""
        return Table(self.name, table)

    def __str__(self) -> str:
        """String view of schema interface."""
        return f'<{self.__class__.__name__}({self.name})>'
    
    def __repr__(self) -> str:
        """Interactive representation of schema interface."""
        return str(self)


# database schema instance variables
user = Schema('user')
observation = Schema('observation')
recommendation = Schema('recommendation')
model = Schema('model')
message = Schema('message')
