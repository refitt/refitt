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

"""Initialize database."""


# standard libs
import logging
from functools import partial

# internal libs
from ....core.config import ConfigurationError
from ....core.exceptions import log_exception
from ....database import init_database, drop_database, load_records

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from sqlalchemy.exc import DatabaseError


PROGRAM = 'refitt database init'
USAGE = f"""\
usage: {PROGRAM} [-h] [--drop] [--core | --test]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --drop             Drop existing tables.
    --core             Load core data.
    --test             Load test data.
-h, --help             Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class InitDatabaseApp(Application):
    """Application class for database init entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    drop_tables: bool = False
    interface.add_argument('--drop', action='store_true', dest='drop_tables')

    load_core: bool = False
    load_test: bool = False
    load_interface = interface.add_mutually_exclusive_group()
    load_interface.add_argument('--core', action='store_true', dest='load_core')
    load_interface.add_argument('--test', action='store_true', dest='load_test')

    exceptions = {
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        DatabaseError: partial(log_exception, logger=log.critical,
                               status=exit_status.runtime_error),
        ConfigurationError: partial(log_exception, logger=log.critical,
                                    status=exit_status.bad_config),
    }

    def run(self) -> None:
        """Business logic of command."""
        if self.drop_tables:
            drop_database()
        init_database()
        if self.load_core:
            load_records('core')
        if self.load_test:
            load_records('test')
