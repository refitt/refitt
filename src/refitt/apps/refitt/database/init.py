# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Initialize database."""


# standard libs
from functools import partial

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from sqlalchemy.exc import DatabaseError

# internal libs
from refitt.core.exceptions import handle_exception
from refitt.core.config import config
from refitt.core.logging import Logger
from refitt.database import create_all, drop_all, load_all
from refitt.database.interface import engine

# public interface
__all__ = ['InitDatabaseApp', ]

# application logger
log = Logger.with_name('refitt')


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
        DatabaseError: partial(handle_exception, logger=log,
                               status=exit_status.runtime_error),
        **Application.exceptions
    }

    def run(self) -> None:
        """Business logic of command."""
        if 'host' in config.database and config.database.host not in ('localhost', '127.0.0.1'):
            response = input(f'Connected to remote database ({engine.url}), proceed ([Y]/n): ')
            if response.lower() not in ('y', 'yes'):
                raise RuntimeError('Missing confirmation')
        if self.drop_tables:
            drop_all()
        create_all()
        if self.load_core:
            load_all('core')
        if self.load_test:
            load_all('test')
