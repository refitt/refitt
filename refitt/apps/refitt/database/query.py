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

"""Query database for records or statistics."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Union, TypeVar, Any

# standard libs
import sys
import json
import logging
from datetime import datetime
from functools import partial

# internal libs
from ....core.config import ConfigurationError
from ....core.exceptions import log_exception
from ....database.model import Base, Column, tables
from ....database.core import Session

# external libs
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, DataError
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table


PROGRAM = 'refitt database query'
USAGE = f"""\
usage: {PROGRAM} [-h] TABLE[.RELATION]... [COND...] [--count | --limit NUM]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
TABLE[.RELATION ...]   Table name with relationship path.
COND...                Filters (e.g., `name==foo`).

options:
-c, --count            Display row count.
-l, --limit            Limit number of returned rows.
-h, --help             Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


__VT = TypeVar('__VT', str, int, float, type(None), datetime)
def _typed(value: str) -> __VT:
    """Automatically coerce string to typed value."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() in ('null', ):
        return None
    elif value.lower() in ('true', ):
        return True
    elif value.lower() in ('false', ):
        return False
    else:
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S%z')
        except ValueError:
            return value


def check_relation(target: Base, *path: str) -> Union[Base, Column]:
    try:
        if not path:
            return target
        else:
            if hasattr(target, 'relationships') and path[0] in target.relationships:
                return check_relation(target.relationships[path[0]], *path[1:])
            else:
                return check_relation(getattr(target, path[0]), *path[1:])
    except AttributeError as error:
        raise ArgumentError(str(error)) from error


def get_path(target: str) -> Tuple[str, List[str]]:
    """The top-level table name and possibly the member relationship path."""
    table, *relationships = target.split('.')
    if table not in tables:
        raise ArgumentError(f'Table does not exist, \'{table}\'')
    check_relation(tables[table], *relationships)
    return table, relationships


def query_table(__name: str, limit: int = None, count: bool = False, **filters) -> Union[List[Base], int]:
    """Query a given table by `__name` with `filters`."""
    session = Session()
    query = session.query(tables[__name])
    for field, value in filters.items():
        query = query.filter_by(**{field: value})
    if count is True:
        return query.count()
    if limit is not None:
        query = query.limit(limit)
    return query.all()


class QueryDatabaseApp(Application):
    """Application class for database query entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    target: str = None
    interface.add_argument('target')

    filters: List[str] = None
    interface.add_argument('filters', nargs='*', default=[])

    limit: int = None
    interface.add_argument('-l', '--limit', type=int, default=limit)

    show_count: bool = False
    interface.add_argument('-c', '--count', dest='show_count', action='store_true')

    format_json: bool = False
    interface.add_argument('--json', action='store_true', dest='format_json')

    exceptions = {
        ArgumentError: partial(log_exception, logger=log.critical,
                               status=exit_status.bad_argument),
        InvalidRequestError: partial(log_exception, logger=log.critical,
                                     status=exit_status.bad_argument),
        ProgrammingError: partial(log_exception, logger=log.critical,
                                  status=exit_status.bad_argument),
        DataError: partial(log_exception, logger=log.critical,
                           status=exit_status.bad_argument),
        ConfigurationError: partial(log_exception, logger=log.critical,
                                    status=exit_status.bad_config),
    }

    session: Session = None

    def run(self) -> None:
        """Business logic of command."""
        self.check_args()
        name, path = get_path(self.target)
        results = self.run_query(name)
        if not results:
            return
        if isinstance(results, list):
            for attr in path:
                results = [getattr(record, attr) for record in results]
            self.print_all(results)
        else:
            print(results)

    def run_query(self, __name: str) -> Union[List[Base], Any]:
        return query_table(__name, limit=self.limit, count=self.show_count, **{
            field: _typed(value) for field, value in [
                arg.split('==') for arg in self.filters
            ]
        })

    def print_all(self, results: List[Base]) -> None:
        """Pretty-print a list of records."""
        if self.format_json:
            self.print_json(results)
        else:
            self.print_table(results)

    @staticmethod
    def print_json(results: List[Base]) -> None:
        """Format records as JSON text."""
        if hasattr(results[0], 'to_json'):
            data = [record.to_json(join=False) for record in results]
        else:
            data = results
        if sys.stdout.isatty():
            Console().print(Syntax(json.dumps(data, indent=4), 'json',
                                   word_wrap=True, theme='monokai',
                                   background_color='default'))
        else:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)

    @staticmethod
    def print_table(results: List[Base]) -> None:
        """Format records as an ASCII table."""
        if hasattr(results[0], 'columns'):
            _, *fields = results[0].columns
            table = Table(title=None)
            table.add_column('id', justify='right', style='cyan')
            for name in fields:
                table.add_column(name, justify='left')
            for record in results:
                table.add_row(*map(str, record.to_tuple()))
            Console().print(table)
        else:
            for result in results:
                print(result)

    def check_args(self):
        for option in self.filters:
            if '==' not in option:
                raise ArgumentError(f'Positional arguments should have equality syntax, \'{option}\'')
