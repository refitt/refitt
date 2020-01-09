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

"""Initialize the REFITT database."""

# type annotations
from __future__ import annotations
from typing import List

# standard libs
import functools

# internal libs
from ....database.client import DatabaseClient
from ....database.config import connection_info
from ....assets import load_asset
from ....core.logging import Logger, SYSLOG_HANDLER
from ....core.exceptions import log_and_exit
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = f'{__appname__} database init'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} NAME [NAME...] [--all] [--drop] [--dry-run]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

options:
    --all                    Initialize all database objects.
    --drop                   Apply drop on objects before re-initializing.
    --dry-run                Show SQL without executing.
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger.with_name('.'.join(PROGRAM.split()))


# initialization order of schemas and tables based on
# foreign key constraint dependencies
DATABASE_OBJECTS = (
    'user',
    'user.facility',
    'user.user',
    'user.facility_map',
    'user.auth',
    'observation',
    'observation.object_type',
    'observation.object',
    'observation.source_type',
    'observation.source',
    'observation.observation_type',
    'observation.observation',
    'observation.alert',
    'observation.file',
    'recommendation',
    'recommendation.recommendation_group',
    'recommendation.recommendation_object',
    'recommendation.recommendation',
    'model',
    'model.model_type',
    'model.model',
    'message',
    'message.message_topic',
    'message.message_level',
    'message.message_host',
    'message.message'
)


DROP_TABLE = 'DROP TABLE {name}'
DROP_SCHEMA = 'DROP SCHEMA {name}'


class Init(Application):
    """Initialize the REFITT database."""

    interface = Interface(PROGRAM, USAGE, HELP)

    names: List[str] = []
    interface.add_argument('names', metavar='NAME', nargs='*')

    all_names: bool = False
    interface.add_argument('-a', '--all', action='store_true', dest='all_names')

    drop: bool = False
    interface.add_argument('--drop', action='store_true')

    dry_run: bool = False
    interface.add_argument('--dry-run', action='store_true')

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Initialize Database."""

        if self.names and self.all_names:
            raise ArgumentError('Using --all with specified objects is ambiguous')

        if self.all_names:
            log.debug('given --all flag, including all objects')
            self.names = DATABASE_OBJECTS

        else:
            for name in set(self.names) - set(DATABASE_OBJECTS):
                log.critical(f'"{name}" is not a recognized database object')
                return
            # put names in DATABASE_OBJECTS order
            self.names = [name for name in DATABASE_OBJECTS if name in self.names]

        if self.dry_run is True:
            log.debug('dry-run: showing SQL')
            print(self.schema)
            return

        info = connection_info()
        if 'tunnel' not in info:
            with DatabaseClient(**info['server']) as client:
                for name in self.names:
                    quoted = name if '.' not in name else '"{}"."{}"'.format(*name.split('.'))
                    if self.drop is True:
                        QUERY = DROP_TABLE if '.' in name else DROP_SCHEMA
                        QUERY = QUERY.format(name=quoted)
                        client.engine.execute(QUERY)
                        log.info(QUERY.lower().replace('drop', 'dropped'))
                    client.engine.execute(self.load_sql(name))
                    log.info(f'initialed {name}')
        else:
            with DatabaseClient(**info['server']).use_tunnel(**info['tunnel']) as client:
                for name in self.names:
                    log.info(f'initializing {name}')
                    client.engine.execute(self.load_sql(name))

    @functools.lru_cache(maxsize=len(DATABASE_OBJECTS))
    def load_sql(self, name: str) -> str:
        """Load and strip SQL from package file."""
        return '\n'.join(list(filter(lambda line: not line.startswith('--'),
                                     load_asset(f'database/{name}.sql').strip().split('\n'))))

    @property
    @functools.lru_cache(maxsize=1)
    def schema(self) -> str:
        """Load and format full database schema."""
        return '\n\n'.join(list(map(self.load_sql, self.names)))

    def __enter__(self) -> Init:
        """Initialize resources."""

        if self.syslog:
            log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        elif self.verbose:
            log.handlers[0].level = log.levels[1]
        else:
            log.handlers[0].level = log.levels[2]

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
