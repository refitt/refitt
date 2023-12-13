# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Check database tables."""


# type annotations
from __future__ import annotations
from typing import List, Dict

# standard libs
import functools

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session

# internal libs
from refitt.core.config import config
from refitt.core.logging import Logger
from refitt.database.model import Entity
from refitt.database.connection import default_connection as db

# public interface
__all__ = ['CheckDatabaseApp', ]

# application logger
log = Logger.with_name('refitt')


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


@functools.lru_cache(maxsize=None)
def tables() -> Dict[str, Entity]:
    """Associate in-database table names with ORM tables."""
    return {table.name: table for table in Entity.metadata.sorted_tables}


class CheckDatabaseApp(Application):
    """Application class for database check entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    names: List[str] = []
    interface.add_argument('names', nargs='*', default=names)

    all_names: bool = False
    interface.add_argument('-a', '--all', dest='all_names', action='store_true')

    show_count: bool = False
    interface.add_argument('-c', '--count', dest='show_count', action='store_true')

    scope: str = 'write'
    interface.add_argument('-s', '--scope', default=scope, choices=['read', 'write'])

    engine: Engine = None
    session: scoped_session = None
    schema: str = None

    def run(self) -> None:
        """Business logic of command."""
        self.check_names()
        self.schema = config.database.default.get('schema')
        self.session = db.get_session(db.name_from_scope(self.scope))
        self.engine = db.get_engine(db.name_from_scope(self.scope))
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
            if self.engine.has_table(name, schema=self.schema):
                print(f'{name}: exists')
            else:
                print(f'{name}: missing')

    def check_table_with_count(self, name: str) -> None:
        """Check table exists with count of rows."""
        if not self.engine.has_table(name, schema=self.schema):
            print(f'{name}: missing')
        else:
            count = self.session.query(tables()[name]).count()
            print(f'{name}: {count}')
