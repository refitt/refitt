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
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Union, Optional, Type

# standard libs
import functools
from abc import ABC

# internal libs
from . import client as _client
from .client import DatabaseClient
from refitt.core.logging import Logger

# external libs
from pandas import DataFrame, Series, read_sql
from sqlalchemy.sql import text
from sqlalchemy.engine import Engine, Connection  # noqa (not declared in __all__)
from sqlalchemy.engine.result import ResultProxy


# initialize module level logger
log = Logger(__name__)


# executable interface to the database
Interface = Union[DatabaseClient, Engine, Connection]
Executable = Union[Engine, Connection]


def get_executable(interface: Optional[Interface] = None) -> Executable:
    """
    Passively derive a database engine or direct connection.
    """
    if isinstance(interface, DatabaseClient):
        return interface.engine
    if isinstance(interface, (Engine, Connection)):
        return interface
    if interface is not None:
        raise TypeError(f'expected one of {Interface.__args__}')
    else:
        return _client.connect().engine


def execute(statement: str, interface: Optional[Interface] = None, **params) -> ResultProxy:
    """
    Execute SQL `statement`.

    Arguments
    ---------
    statement: str
        An SQL query to execute.

    interface: `DatabaseClient`, `Engine`, or `Connection`
        A client connection to the database. If None, one will either be created temporarily
        for the lifetime of this query, or if a `refitt.database.core.client._PERSISTENT_CLIENT`
        exists, it will be used. An existing direct `Connection` is also allowed.

    Returns
    -------
    result: `ResultProxy`

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
    return get_executable(interface).execute(text(statement), **params)


def insert(data: DataFrame, schema: str, table: str, interface: Interface = None,
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

    interface: `DatabaseClient`, `Engine`, or `Connection`
        A client connection to the database. If None, one will either be created temporarily
        for the lifetime of this query, or if a `refitt.database.core.client._PERSISTENT_CLIENT`
        exists, it will be used. An existing direct `Connection` is also allowed.

    if_exists: str (default: 'append')
        Action to take if the `table` already exists. (see `pandas.DataFrame.to_sql`).

    index: bool (default: False)
        Whether to include the index for insertion. (see `pandas.DataFrame.to_sql`).

    chunksize: int (default: 10_000)
        Number of rows to insert at a time. (see `pandas.DataFrame.to_sql`).

    See Also
    --------
    - `DataFrame.to_sql`
    """
    return data.to_sql(table, get_executable(interface), schema=schema,
                       if_exists=if_exists, index=index, chunksize=chunksize)


def _select(query: str, interface: Optional[Interface] = None, **params) -> DataFrame:
    return read_sql(text(query), get_executable(interface), params=params)


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


_FIND_DTYPES = """\
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = :schema AND table_name = :table
"""


@functools.lru_cache(maxsize=None)
def get_dtypes(schema: str, table: str) -> DataFrame:
    """List of data types by column name."""
    return _select(_FIND_DTYPES, schema=schema, table=table)


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


def _convert_bytea(series: Series) -> Series:
    """Convert a returned list of bytes characters into continues bytes."""
    return series.str.join(b'')


_dtype_converters = {
    'bytea': _convert_bytea,
}


def select(columns: List[str], schema: str, table: str, interface: Optional[Interface] = None,
           where: List[str] = None, limit: int = None, orderby: str = None, ascending: bool = True,
           join: bool = False, set_index: bool = True) -> DataFrame:
    """
    Construct and execute an SQL query based on the selection criteria.

    Arguments
    ---------
    columns: List[str]
        The names of the columns to return. If None, all columns are returned.

    schema: str
        The name of the database schema to use.

    table: str
        The name of the database table to select from.

    interface: `DatabaseClient`, `Engine`, or `Connection`
        A client connection to the database. If None, one will either be created temporarily
        for the lifetime of this query, or if a `refitt.database.core.client._PERSISTENT_CLIENT`
        exists, it will be used. An existing direct `Connection` is also allowed.

    where: List[str]
        A list of conditional statements, e.g., "foo = 10".

    limit: int
        The number of records to return. If None, do not limit.

    orderby: str
        The name of the column to order records by. If None, do not order.

    ascending: bool (default: True)
        Whether to order as ascending or descending.

    join: bool (default: False)
        Apply automatic, intelligent joins to swap out "_id" foreign keys as their
        associated "_name" values from their parent table.

    set_index: bool (default: True)
        If True and a "`table`_id" column exists, set it as the index.

    Returns
    -------
    table: `DataFrame`
    """
    query = _make_select(columns, schema, table, where=where, limit=limit,
                         orderby=orderby, ascending=ascending, join=join)

    result = _select(query, interface)
    if set_index is True and f'{table}_id' in result.columns:
        result = result.set_index(f'{table}_id')

    # coerce problematic dtypes (e.g., bytea)
    dtypes = get_dtypes(schema, table)
    for dtype_name, dtype_converter in _dtype_converters.items():
        for column_name in dtypes.loc[dtypes.data_type == dtype_name, 'column_name']:
            result[column_name] = dtype_converter(result[column_name])

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


class RecordNotFound(Exception):
    """A record could not be found."""


class Record(ABC):
    """Like dataclass or namedtuple, but more comprehensive."""

    _fields: Tuple[str, ...] = ()
    _masked: bool = False

    # delegate to some other factory method based on uniquely
    # identifiable attribute (e.g., `record_id`).
    _FACTORIES: Dict[str, str] = {}

    def __init__(self, *inst, **fields) -> None:
        """Initialize attributes."""
        if inst and not fields:
            self.__init_move(*inst)
        elif fields and not inst:
            self.__init_base(**fields)
        else:
            raise ValueError(f'{self.__class__.__name__} expects instance or named fields.')

    def __init_move(self, other: Record) -> None:
        """Initialize new Record from existing an instance."""
        self.__init_base(**other.to_dict())

    def __init_base(self, **fields) -> None:
        """Initialize new Record from named fields."""
        for field, value in fields.items():
            if field in self._fields:
                setattr(self, field, value)
            else:
                raise AttributeError(f'"{field}" is not an attribute of {self.__class__.__name__}')
        for field in self._fields[1:]:  # not necessarily the primary key
            if field not in fields:
                raise AttributeError(f'must specify "{field}"')

    @property
    def _values(self) -> tuple:
        """The associated values of the _fields."""
        return tuple(getattr(self, name) for name in self._fields)

    def _repr(self, name: str) -> str:
        """Format the named field (as used in __repr__)."""
        value = repr(getattr(self, name))
        return f'{name}={value}'

    def __str__(self) -> str:
        """String representation."""
        _repr = ', '.join(list(map(self._repr, self._fields)))
        _repr = f'{self.__class__.__name__}({_repr})'
        _repr = _repr if not self._masked else f'<{_repr}>'
        return _repr

    def __repr__(self) -> str:
        """Interactive representation (see also: __str__)."""
        return str(self)

    def copy(self) -> Record:
        """Create a duplicate record."""
        old = self.to_dict()
        return self.__class__.from_dict(old.copy())

    @classmethod
    def from_dict(cls, other: Dict[str, Any]) -> Record:
        """Initialize from a dictionary of values."""
        return cls(**other)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {field: getattr(self, field) for field in self._fields}

    @classmethod
    def from_series(cls, other: Series) -> Record:
        """Initialize from an extracted `pandas.Series`."""
        return cls.from_dict(dict(other))

    @classmethod
    def from_database(cls, interface: Interface = None, **key) -> Record:
        """Fetch record from database."""
        factories = list(cls._FACTORIES)
        if len(key) != 1 or list(key.keys())[0] not in factories:
            raise TypeError('expected one of ' + ', '.join([f'"{name}"' for name in factories]))
        (field, value), = key.items()
        factory = getattr(cls, cls._FACTORIES[field])
        return factory(value, interface=interface)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Record:
        """Initialize from a uniquely identifiable record in the database."""
        records = table.select(where=[f"{field} = '{value}'"], set_index=False, interface=interface)
        if records.empty:
            raise RecordNotFound(f'from "{table.schema}"."{table.name}" where {field}={value}')
        return cls.from_series(records.iloc[0])

    def __eq__(self, other: Record) -> bool:
        """Compare field values."""
        return isinstance(other, Record) and self.to_dict() == other.to_dict()

    def __ne__(self, other: Record) -> bool:
        """Compare field values."""
        return not self == other
