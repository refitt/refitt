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

"""Parse database configuration."""

# standard libs
import os
import functools
import subprocess

# internal libs
from .client import DatabaseClient, ServerAddress, UserAuth
from ..core.config import config, Namespace
from ..core.logging import Logger


# initialize module level logger
log = Logger.with_name(f'refitt.database')


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