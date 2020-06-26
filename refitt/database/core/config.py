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
import functools

# internal libs
from ...core.config import config, ConfigurationError, expand_parameters, VARS
from ...core.logging import Logger
from .types import ServerAddress, UserAuth


# initialize module level logger
log = Logger(__name__)


@functools.lru_cache(maxsize=None)
def connection_info(profile: str = None, database: str = None) -> dict:
    """Parse information from configuration file."""

    # default is local "refitt" database
    if profile is None and 'database' not in config.keys():
        return {'database': {'server': ServerAddress(host='localhost', port=5432),
                             'auth': None,
                             'database': 'refitt'}}

    db_config = config['database']

    # precedence: `profile` > DATABASE_PROFILE > 'default'
    profile = profile if profile is not None else VARS['DATABASE_PROFILE']
    if profile not in db_config:
        raise ConfigurationError(f'database profile not found: {profile}')

    db_config = db_config[profile]
    db_name = database if database is not None else db_config.get('database', 'refitt')
    db_host = db_config.get('host', 'localhost')
    db_port = db_config.get('port', 5432)
    db_user = db_config.get('user', None)
    db_pass = expand_parameters('password', db_config)  # None if absent

    db_auth = None
    if db_user or db_pass:
        db_auth = UserAuth(username=db_user, password=db_pass)

    # base configuration (the database itself)
    info = {'database': {'server': ServerAddress(host=db_host, port=db_port),
                         'auth': db_auth, 'database': db_name}}

    tunnel = db_config.get('tunnel', None)
    if tunnel:

        tunnel_host = tunnel.get('host', None)
        tunnel_port = tunnel.get('port', 22)
        tunnel_bind = tunnel.get('bind', 54321)
        tunnel_user = tunnel.get('user', None)
        tunnel_pass = expand_parameters('password', tunnel)  # None if absent

        if tunnel_host is None:
            raise ConfigurationError('most provide host for tunnel')

        tunnel_auth = None  # will fall back on ~/.ssh/id_rsa
        if tunnel_user or tunnel_pass:
            tunnel_auth = UserAuth(tunnel_user, tunnel_pass)

        # add ssh tunnel in front of database
        info['tunnel'] = {'ssh': ServerAddress(tunnel_host, tunnel_port), 'auth': tunnel_auth,
                          'local': ServerAddress('localhost', tunnel_bind)}
    return info
