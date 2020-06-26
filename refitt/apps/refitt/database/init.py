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
from typing import List, Dict, Tuple, Optional

# standard libs
import os
import io
import functools

# internal libs
from .... import database
from ....assets import find_files, load_asset, load_assets
from ....core.logging import Logger, cli_setup
from ....core.exceptions import log_and_exit
from ....core.config import ConfigurationError
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from pandas import DataFrame, read_json


PROGRAM = f'{__appname__} database init'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} NAME [NAME...] [--all] [--profile NAME]
       {PADDING} [--drop] [--cascade] [--data] [--dry-run]
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
    --all             Initialize all database objects.
    --drop            Apply drop on objects before re-initializing.
    --cascade         Recursively drop using 'DROP ... CASCADE'
    --data            Load initial data into tables.
    --profile  NAME   Name of database profile (e.g., "test").
    --dry-run         Show SQL without executing.
-d, --debug           Show debugging messages.
-v, --verbose         Show information messages.
    --syslog          Use syslog style messages.
-h, --help            Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger(__name__)


# initialization order of schemas and tables based on
# foreign key constraint dependencies
DATABASE_OBJECTS = (
    'profile',
    'profile.facility',
    'profile.user',
    'profile.facility_map',
    'auth',
    'auth.client',
    'auth.access',
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
    'recommendation.recommendation',
    'model',
    'model.type',
    'model.model',
    'message',
    'message.level',
    'message.host',
    'message.producer',
    'message.topic',
    'message.server',
    'message.message',
    'message.consumer',
    'message.access'
)


DROP_TABLE = 'DROP TABLE IF EXISTS {name}'
DROP_SCHEMA = 'DROP SCHEMA IF EXISTS {name}'


class Init(Application):
    """Initialize the REFITT database."""

    interface = Interface(PROGRAM, USAGE, HELP)

    names: List[str] = []
    interface.add_argument('names', metavar='NAME', nargs='*')

    all_names: bool = False
    interface.add_argument('-a', '--all', action='store_true', dest='all_names')

    drop: bool = False
    interface.add_argument('--drop', action='store_true')

    cascade: bool = False
    interface.add_argument('--cascade', action='store_true')

    include_data: bool = False
    interface.add_argument('--data', action='store_true', dest='include_data')

    profile: Optional[str] = None
    interface.add_argument('--profile', default=os.getenv('REFITT_DATABASE_PROFILE'))

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
        ConfigurationError: functools.partial(log_and_exit, logger=log.critical,
                                            status=exit_status.bad_config),
    }

    def run(self) -> None:
        """Initialize Database."""

        if self.names and self.all_names:
            raise ArgumentError('Using --all with specified objects is ambiguous')

        if self.all_names:
            self.names = list(DATABASE_OBJECTS)

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

        if self.drop:
            for name in self.names:
                query = DROP_TABLE if '.' in name else DROP_SCHEMA
                query = query.format(name=self.quoted(name))
                database.execute(query)
                log.warning(query.lower().replace(' if exists', '').replace('cascade', '[cascade]'))

        for name in self.names:
            database.execute(self.schemas[name])
            log.info(f'initialized {name}')

        if self.include_data:
            for name in self.names:
                if name in self.data:
                    schema, table = name.split('.')
                    database.insert(self.data[name], schema, table)
                    log.info(f'loaded initial data into {name}')

    @staticmethod
    def quoted(name: str) -> str:
        """Quote schema and table name if necessary."""
        return f'"{name}"' if '.' not in name else '"{}"."{}"'.format(*name.split('.'))

    @property
    @functools.lru_cache(maxsize=None)
    def schemas(self) -> Dict[str, str]:
        """Load and strip SQL from /assets."""
        return {os.path.basename(path)[:-4]: self.strip_comments(query)
                for path, query in load_assets('database/schema/*.sql').items()}

    @staticmethod
    def strip_comments(query: str) -> str:
        """String comment lines from SQL `query`."""
        return '\n'.join([line for line in query.strip().split('\n')
                          if not line.startswith('--')])

    @property
    def schema(self) -> str:
        """One monolithic SQL for --dry-run."""
        return '\n\n'.join([query for name, query in self.schemas.items()
                            if name in self.names])

    @property
    @functools.lru_cache(maxsize=None)
    def data(self) -> Dict[str, DataFrame]:
        """The data files (JSON) as text."""
        return dict(map(self.load_data, find_files('database/metadata/*.json')))

    @staticmethod
    def load_data(asset: str) -> Tuple[str, DataFrame]:
        """Load dataset from `asset` file path."""
        basename = os.path.basename(asset)
        schema, table, ftype = basename.split('.')
        data = io.BytesIO(load_asset(asset, mode='rb'))
        return f'{schema}.{table}', read_json(data).set_index(f'{table}_id')

    def __enter__(self) -> Init:
        """Initialize resources."""
        cli_setup(self)
        database.connect(profile=self.profile)
        log.info(f'initializing database (profile={self.profile})')

        global DROP_TABLE, DROP_SCHEMA
        if self.cascade:
            DROP_TABLE += ' CASCADE'
            DROP_SCHEMA += ' CASCADE'

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
