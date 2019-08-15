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
import functools
import subprocess

# internal libs
from .client import DatabaseClient, ServerAddress, UserAuth
from ..core.config import config, Namespace
from ..core.logging import logger
from . import queries

# external libs
from pandas import DataFrame, read_sql


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


class DatabaseMixin:
    """Access and query methods for interacting with the database."""

    def execute(self, query: str) -> DataFrame:
        """Submit query to database with `sql` statement."""
        info = connection_info()
        if 'tunnel' not in info:
            with DatabaseClient(**info['server']) as client:
                return read_sql(query, client.connection)
        else:
            with DatabaseClient(**info['server']).use_tunnel(**info['tunnel']) as client:
                return read_sql(query, client.connection)


class ObservationSchema(DatabaseMixin):
    """Interface with "Observation" schema within the "refitt" database."""

    @property
    @functools.lru_cache(maxsize=1)
    def object_types(self) -> DataFrame:
        """The "Observation"."ObjectType" table."""
        return self.execute(queries.OBJECT_TYPE).set_index('ObjectTypeID')


# database schema instances
observation = ObservationSchema()