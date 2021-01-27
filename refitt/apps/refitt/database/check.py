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

"""Check database tables."""


# type annotations
from __future__ import annotations
from typing import List, Dict

# standard libs
import logging
from functools import partial, lru_cache

# internal libs
from ....core.config import ConfigurationError
from ....core.exceptions import log_exception
from ....database.model import Base
from ....database.core import engine, schema, Session

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = 'refitt database check'
USAGE = f"""\
usage: {PROGRAM} [-h] [TBL [TBL ...] | --all] [--count]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
TBL...                 Names of tables to check.

options:
-a, --all              Check all tables.
-c, --count            Display row count with table check.
-h, --help             Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


@lru_cache(maxsize=None)
def tables() -> Dict[str, Base]:
    """Associate in-database table names with ORM tables."""
    return {table.name: table for table in Base.metadata.sorted_tables}


class CheckDatabaseApp(Application):
    """Application class for database check entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    names: List[str] = []
    interface.add_argument('names', nargs='*', default=names)

    all_names: bool = False
    interface.add_argument('-a', '--all', dest='all_names', action='store_true')

    show_count: bool = False
    interface.add_argument('-c', '--count', dest='show_count', action='store_true')

    exceptions = {
        ArgumentError: partial(log_exception, logger=log.critical,
                               status=exit_status.bad_argument),
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        ConfigurationError: partial(log_exception, logger=log.critical,
                                    status=exit_status.bad_config),
    }

    session: Session = None

    def run(self) -> None:
        """Business logic of command."""
        self.check_names()
        self.session = Session()
        for name in self.names:
            self.check_table(name)

    def check_names(self) -> None:
        """Validate table name arguments with --all flag."""
        if self.names and self.all_names:
            raise ArgumentError('cannot use --all with named objects')
        if self.all_names:
            self.names = list(tables())
        else:
            for name in self.names:
                if name not in tables():
                    raise ArgumentError(f'"{name}" is not a recognized table')

    def check_table(self, name: str) -> None:
        """Check table exists and optionally report count of rows."""
        if self.show_count:
            self.check_table_with_count(name)
        else:
            if engine.has_table(name, schema=schema):
                print(f'{name}: exists')
            else:
                print(f'{name}: missing')

    def check_table_with_count(self, name: str) -> None:
        """Check table exists with count of rows."""
        if not engine.has_table(name, schema=schema):
            print(f'{name}: missing')
        else:
            count = self.session.query(tables()[name]).count()
            print(f'{name}: {count}')
