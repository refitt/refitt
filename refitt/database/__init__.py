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
import datetime
from typing import Dict, Any

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


class TableInterface:
    """High-level interface to REFITT's database tables."""

    _where_templates: Dict[str, str]


class DatabaseMixin:
    """Access and query methods for interacting with the database."""

    def execute(self, query: str) -> DataFrame:
        """
        Execute SQL `query` statement.

        See Also:
            `pandas.read_sql`
        """

        info = connection_info()
        USERNAME = info['server']['auth'].username
        PASSWORD = info['server']['auth'].password
        DATABASE = info['server']['database']

        if 'tunnel' not in info:
            HOST = info['server']['server'].host
            PORT = info['server']['server'].port
            engine = create_engine(f'postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}')
            try:
                data = read_sql(query, engine)
            finally:
                engine.dispose()
        else:
            with SSHTunnelForwarder((info['tunnel']['ssh'].host, info['tunnel']['ssh'].port), 
                                    ssh_username=info['tunnel']['auth'].username, ssh_password=info['tunnel']['auth'].password, 
                                    remote_bind_address=(info['server']['server'].host, info['server']['server'].port), 
                                    local_bind_address=(info['tunnel']['local'].host, info['tunnel']['local'].port)) as tunnel: 
                 
                engine = create_engine(f'postgresql://{USERNAME}:{PASSWORD}@{tunnel.local_bind_host}:'
                                       f'{tunnel.local_bind_port}/{DATABASE}')
                try: 
                    data = read_sql(query, engine) 
                finally: 
                    engine.dispose() 
        
        return data


    def insert(self, data: DataFrame, table: str, schema: str) -> None:
        """
        Insert `data` into `schema`.`table`.

        See Also:
            `pandas.DataFrame.to_sql`
        """

        info = connection_info()
        USERNAME = info['server']['auth'].username
        PASSWORD = info['server']['auth'].password
        DATABASE = info['server']['database']

        if 'tunnel' not in info:
            HOST = info['server']['server'].host
            PORT = info['server']['server'].port
            engine = create_engine(f'postgresql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}')
            try:
                data.to_sql(table, engine, schema=schema, if_exists='append', index=False, chunksize=10000)
            finally:
                engine.dispose()
        else:
            with SSHTunnelForwarder((info['tunnel']['ssh'].host, info['tunnel']['ssh'].port), 
                                    ssh_username=info['tunnel']['auth'].username, ssh_password=info['tunnel']['auth'].password, 
                                    remote_bind_address=(info['server']['server'].host, info['server']['server'].port), 
                                    local_bind_address=(info['tunnel']['local'].host, info['tunnel']['local'].port)) as tunnel: 
                 
                engine = create_engine(f'postgresql://{USERNAME}:{PASSWORD}@{tunnel.local_bind_host}:'
                                       f'{tunnel.local_bind_port}/{DATABASE}')
                try: 
                    data.to_sql(table, engine, schema=schema, if_exists='append', index=False, chunksize=10000)
                finally: 
                    engine.dispose() 

    @staticmethod
    def _join_where_clauses(query: str, templates: Dict[str, str],
                            conditions: Dict[str, Any]) -> str:
        """
        Construct an SQL query by merging the base select statement with any
        where `conditions` that may exist using defined `templates`.
        """
        if not conditions:
            return query
        else:
            where_statements = '\nAND\n'.join([templates[field].format(**{field: value})
                                               for field, value in conditions.items()])
            return '\nWHERE\n'.join([query, where_statements])


class UserSchema(DatabaseMixin):
    """Interface with "User" schema within the "refitt" database."""
    
    _user_conditions: dict = {
        'user_id': queries.USER_WHERE_USER_ID,
        'user_name': queries.USER_WHERE_USER_NAME,
    }

    def user(self, **conditions) -> DataFrame:
        """Query "User."User" table with optional _where_ `conditions`."""
        query = self._join_where_clauses(queries.USER, self._user_conditions, conditions)
        return self.execute(query).set_index('user_id')

    _auth_conditions: dict = {
        'auth_id':    queries.AUTH_WHERE_AUTH_ID,
        'auth_level': queries.AUTH_WHERE_AUTH_LEVEL,
        'auth_key':   queries.AUTH_WHERE_AUTH_KEY,
        'auth_token': queries.AUTH_WHERE_AUTH_TOKEN,
        'auth_valid': queries.AUTH_WHERE_AUTH_VALID,
        'auth_time':  queries.AUTH_WHERE_AUTH_TIME,
        'user_id':    queries.AUTH_WHERE_USER_ID,
    }

    def auth(self, **conditions) -> DataFrame:
        """Query "User."Auth" table with optional _where_ `conditions`."""
        query = self._join_where_clauses(queries.AUTH, self._auth_conditions, conditions)
        return self.execute(query).set_index('auth_id')
    
    def gen_auth(self, level: int, key: str, user_id: int, check: bool = True) -> DataFrame:
        """
        Generate a new set of user authentication credentials.

        Arguments
        ---------
        level: int
            The `auth_level` to use.

        key: str
            The `auth_key` this new token is to be associated with.

        user_id: int
            The `user_id` to associate with these credentials.
        
        check: bool (default=True)
            Validate the `user_id` exists in the "User"."User" table.

        Returns
        -------
        auth: pandas.DataFrame
            A dataframe with a single row (auth_level, auth_key, auth_token, auth_valid,
            auth_time, user_id). The auth_id is auto-generated by the database upon insertion.
            auth_valid is always set to True.
        
        See also
        --------
        .gen_key() -> str
            Generate a new auth_key.
        """
        _level, _key, _user_id = int(level), str(key), int(user_id)
        if _level < 0:
            raise ValueError(f'{self.__class__.__name__}.gen_auth expect a non-negative integer for `level`.')
        if len(_key) != 16:
            raise ValueError(f'{self.__class__.__name__}.gen_auth expects a 16-character string for `key`.')
        if _user_id < 0:
            raise ValueError(f'{self.__class__.__name__}.gen_auth expect a non-negative integer for `user_id`.')
        if check and self.user(user_id=_user_id).empty:
            raise ValueError(f'{self.__class__.__name__}.gen_auth: user_id={_user_id} not found in "User"."User".')

        return DataFrame({'AuthID': [0],
                          'AuthLevel': [_level],
                          'AuthKey': [_key],
                          'AuthToken': [secrets.token_hex(32)],
                          'AuthValid': [True],
                          'AuthTime': [datetime.datetime.now()],
                          'UserID': [_user_id]
                          }).set_index('AuthID')

    def gen_key(self) -> str:
        """
        Generate a new auth_key.

        Returns
        -------
        auth_key: str
            A 16-character hexadecimal string.
        """
        return secrets.token_hex(8)


class ObservationSchema(DatabaseMixin):
    """Interface with "Observation" schema within the "refitt" database."""

    def object_types(self) -> DataFrame:
        """The "Observation"."ObjectType" table."""
        return self.execute(queries.OBJECT_TYPE).set_index('ObjectTypeID')


# global database schema instances
user = UserSchema()
observation = ObservationSchema()
