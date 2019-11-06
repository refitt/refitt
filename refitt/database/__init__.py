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

"""Access and API for REFITT database."""

# standard libs
import os
import secrets
import functools
import subprocess
import inspect
from datetime import datetime
from abc import ABC as Interface
from typing import Tuple, Dict, Any

# internal libs
from .client import DatabaseClient, ServerAddress, UserAuth
from ..core.config import Namespace
from ..core.logging import logger
from . import queries

# external libs
from pandas import DataFrame, read_sql
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


# initialize module level logger
log = logger.with_name(f'refitt.database')


def expand_parameters(prefix: str, namespace: Namespace) -> str:
    """Substitute values into namespace if `_env` or `_eval` present."""
    value = None
    count = 0
    for key in filter(lambda key: key.startswith(prefix), namespace.keys()):
        count += 1
        if count > 1:
            raise ValueError(f'more than one variant of "{prefix}" in configuration file')
        if key.endswith('_env'):
            value = os.getenv(namespace[key])
            log.debug(f'expanded "{prefix}" from configuration as environment variable')
        elif key.endswith('_eval'):
            value = subprocess.check_output(namespace[key].split()).decode().strip()
            log.debug(f'expanded "{prefix}" from configuration as shell command')
        elif key == prefix:
            value = namespace[key]
        else:
            raise ValueError(f'unrecognized variant of "{prefix}" ({key}) in configuration file')
    return value


@functools.lru_cache(maxsize=1)
def connection_info() -> dict:
    """Parse information from configuration file."""

    from ..core.config import config

    server = config['database']['server']
    server_user = None if 'user' not in server else server['user']
    server_password = expand_parameters('password', server)

    info = {
        'server': {
            'server': ServerAddress(host=server['host'], port=server['port']),
            'auth': UserAuth(username=server_user, password=server_password),
            'database': server['database']
        }
    }

    if 'tunnel' in config['database']:
        tunnel = config['database']['tunnel']
        tunnel_user = None if 'user' not in tunnel else tunnel['user']
        tunnel_password = expand_parameters('password', tunnel)
        info['tunnel'] = {
                'ssh': ServerAddress(host=tunnel['host'], port=tunnel['port']),
                'auth': UserAuth(username=tunnel_user, password=tunnel_password),
                'local': ServerAddress(host='localhost', port=tunnel['bind'])
        }

    return info


def execute(self, query: str) -> DataFrame:
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


def insert(self, data: DataFrame, table: str, schema: str, if_exists: str = 'append',
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


QUERY_TEMPLATE = """\
SELECT
    {columns}

FROM
    {table}
"""


# class Query():
#     """Construct, preview, and execute database queries."""

#     def __init__(self, schema: str, table: str, columns: Tuple[str], 
#                  limit: int = None, **where: Dict[str, Any]) -> None:
        
#         _table = f'"{schema}"."{table}" as "{table}"'
#         if isinstance(columns, dict):
#             _columns = [f'"{table}"."{name}" as "{alias}"' for name, alias in columns.items()]
#         else:
#             _columns = [f'"{table}"."{name}" as "{name}"' for name in columns]
        
#         # operator mapping
#         where_map = {'': '=', 'not': '!=', 'lt': '<', 'le': '<=',
#                      'gt': '>', 'ge': '>=', 'any': 'IN', 'not_any': 'NOT IN'}
#         where_type = {f'where_{name}': op for name, op in where_map.items()}

#         for keyword in where.keys():
#             if keyword not in where_type.key():
#                 raise

#         _constrains = []
#         for name, constrain in where.items():
#             _constrains.append(self._format_constrain(constrain, op='='))
#         for name, constrain in where_not.items():
#             _constrains.append(self._format_constrain(constrain, op='!='))
#         for name, constrain in where_lt.items():
#             _constrains.append(self._format_constrain(constrain, op='!='))
#         for name, constrain in where_gt.items():
#             _constrains.append(self._format_constrain(constrain, op='!='))
#         for name, constrain in where_not.items():
#             _constrains.append(self._format_constrain(constrain, op='!='))
#         for name, constrain in where_not.items():
#             _constrains.append(self._format_constrain(constrain, op='!='))



# class Table(Interface):
#     """Abstract base class for Database tables."""
    
#     columns: Tuple[str] = ()

#     def __str__(self) -> str:
#         """String view of the Table."""
#         columns = ', '.join([f'"{name}"' for name in self.columns])
#         return f'<Table:{self.__class__.__name__}({names})>'
    
#     def __repr__(self) -> str:
#         """Live representation of the Table."""
#         return str(self)


# class Schema(Interface):
#     """Access and query methods for interacting with the database."""

#     @staticmethod
#     def _join_where_clauses(query: str, templates: Dict[str, str],
#                             conditions: Dict[str, Any]) -> str:
#         """
#         Construct an SQL query by merging the base select statement with any
#         where `conditions` that may exist using defined `templates`.
#         """
#         if not conditions:
#             return query
#         else:
#             where_statements = '\nAND\n'.join([templates[field].format(**{field: value})
#                                                for field, value in conditions.items()])
#             return '\nWHERE\n'.join([query, where_statements])
    
#     def __str__(self) -> str:
#         """List of tables in the schema."""
#         tables = ', '.join([str(name) for name, method in
#                            inspect.getmembers(self, lambda member: isinstance(member, Table))])
#         return f'<Schema:{self.__class__.__name__}({tables})>'
    
#     def __repr__(self) -> str:
#         """List of tables in the schema."""
#         return str(self)


# class UserSchema(DatabaseMixin):
#     """Interface with "User" schema within the "refitt" database."""
    
#     _user_conditions: dict = {
#         'user_id': queries.USER_WHERE_USER_ID,
#         'user_name': queries.USER_WHERE_USER_NAME,
#     }

#     def user(self, **conditions) -> DataFrame:
#         """Query "User."User" table with optional _where_ `conditions`."""
#         query = self._join_where_clauses(queries.USER, self._user_conditions, conditions)
#         return self.execute(query).set_index('user_id')

#     _auth_conditions: dict = {
#         'auth_id':    queries.AUTH_WHERE_AUTH_ID,
#         'auth_level': queries.AUTH_WHERE_AUTH_LEVEL,
#         'auth_key':   queries.AUTH_WHERE_AUTH_KEY,
#         'auth_token': queries.AUTH_WHERE_AUTH_TOKEN,
#         'auth_valid': queries.AUTH_WHERE_AUTH_VALID,
#         'auth_time':  queries.AUTH_WHERE_AUTH_TIME,
#         'user_id':    queries.AUTH_WHERE_USER_ID,
#     }

#     def auth(self, **conditions) -> DataFrame:
#         """Query "User."Auth" table with optional _where_ `conditions`."""
#         query = self._join_where_clauses(queries.AUTH, self._auth_conditions, conditions)
#         return self.execute(query).set_index('auth_id')
    
#     def gen_auth(self, level: int, key: str, user_id: int, check: bool = True) -> DataFrame:
#         """
#         Generate a new set of user authentication credentials.

#         Arguments
#         ---------
#         level: int
#             The `auth_level` to use.

#         key: str
#             The `auth_key` this new token is to be associated with.

#         user_id: int
#             The `user_id` to associate with these credentials.
        
#         check: bool (default=True)
#             Validate the `user_id` exists in the "User"."User" table.

#         Returns
#         -------
#         auth: pandas.DataFrame
#             A dataframe with a single row (auth_level, auth_key, auth_token, auth_valid,
#             auth_time, user_id). The auth_id is auto-generated by the database upon insertion.
#             auth_valid is always set to True.
        
#         See also
#         --------
#         .gen_key() -> str
#             Generate a new auth_key.
#         """
#         _level, _key, _user_id = int(level), str(key), int(user_id)
#         if _level < 0:
#             raise ValueError(f'{self.__class__.__name__}.gen_auth expect a non-negative integer for `level`.')
#         if len(_key) != 16:
#             raise ValueError(f'{self.__class__.__name__}.gen_auth expects a 16-character string for `key`.')
#         if _user_id < 0:
#             raise ValueError(f'{self.__class__.__name__}.gen_auth expect a non-negative integer for `user_id`.')
#         if check and self.user(user_id=_user_id).empty:
#             raise ValueError(f'{self.__class__.__name__}.gen_auth: user_id={_user_id} not found in "User"."User".')

#         return DataFrame({'AuthID': [0],
#                           'AuthLevel': [_level],
#                           'AuthKey': [_key],
#                           'AuthToken': [secrets.token_hex(32)],
#                           'AuthValid': [True],
#                           'AuthTime': [datetime.now()],
#                           'UserID': [_user_id]
#                           }).set_index('AuthID')

#     def gen_key(self) -> str:
#         """
#         Generate a new auth_key.

#         Returns
#         -------
#         auth_key: str
#             A 16-character hexadecimal string.
#         """
#         return secrets.token_hex(8)


# class ObservationSchema(DatabaseMixin):
#     """Interface with "Observation" schema within the "refitt" database."""
    
#     _object_type_conditions: dict = {
#         'object_type_id': queries.OBJECT_TYPE_WHERE_OBJECT_TYPE_ID,
#         'object_type_name': queries.OBJECT_TYPE_WHERE_OBJECT_TYPE_NAME,
#         'object_type_description': queries.OBJECT_TYPE_WHERE_OBJECT_TYPE_DESCRIPTION,
#     }

#     def object_types(self, **conditions) -> DataFrame:
#         """Query "Observation."ObjectType" table with optional _where_ `conditions`."""
#         query = self._join_where_clauses(queries.OBJECT_TYPE, self._object_type_conditions, conditions)
#         return self.execute(query).set_index('object_type_id')
    
#     _source_conditions: dict = {
#         'source_id': queries.SOURCE_WHERE_SOURCE_ID,
#         'source_name': queries.SOURCE_WHERE_SOURCE_NAME,
#         'source_description': queries.SOURCE_WHERE_SOURCE_DESCRIPTION,
#         'source_reference': queries.SOURCE_WHERE_SOURCE_REFERENCE,
#     }

#     def source(self, **conditions) -> DataFrame:
#         """Query "Observation."Source" table with optional _where_ `conditions`."""
#         query = self._join_where_clauses(queries.SOURCE_TYPE, self._source_conditions, conditions)
#         return self.execute(query).set_index('source_id')


# # global database schema instances
# user = UserSchema()
# observation = ObservationSchema()


# users = User().Auth(select=['AuthKey', 'AuthToken', 'AuthTime'],
#                     where={'AuthValid': True, 'AuthLevel': [0, 1, 2]},
#                     where_gt={''}
#                     limit=10)