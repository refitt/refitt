# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Query database for records or statistics."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Union, TypeVar, Any

# standard libs
import re
import sys
import json
import logging
from datetime import datetime
from functools import partial, cached_property
from dataclasses import dataclass

# external libs
from sqlalchemy import Column, type_coerce
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, DataError
from sqlalchemy.types import JSON
from sqlalchemy.sql.elements import BinaryExpression
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

# internal libs
from ....core.exceptions import log_exception
from ....database.model import ModelInterface, tables
from ....database.interface import Session

# public interface
__all__ = ['QueryDatabaseApp', ]


PROGRAM = 'refitt database query'
USAGE = f"""\
usage: {PROGRAM} [-h] TABLE[.RELATION]... [COND...] [--count | --limit NUM] [--json]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
TABLE[.RELATION ...]   Table name with relationship path.
COND...                Filters (e.g., `name==foo`).

options:
    --json             Format output as JSON.
-c, --count            Display row count.
-l, --limit            Limit number of returned rows.
-h, --help             Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


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
        InvalidRequestError: partial(log_exception, logger=log.critical,
                                     status=exit_status.bad_argument),
        ProgrammingError: partial(log_exception, logger=log.critical,
                                  status=exit_status.bad_argument),
        DataError: partial(log_exception, logger=log.critical,
                           status=exit_status.bad_argument),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Business logic of command."""
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

    def run_query(self, __name: str) -> Union[List[ModelInterface], Any]:
        return query_table(__name, limit=self.limit, count=self.show_count, filters=self.field_selectors)

    def print_all(self, results: List[ModelInterface]) -> None:
        """Pretty-print a list of records."""
        if self.format_json:
            self.print_json(results)
        else:
            self.print_table(results)

    def print_json(self, results: List[ModelInterface]) -> None:
        """Format records as JSON text."""
        if isinstance(results[0], list):
            self.print_json([record for group in results for record in group])
            return
        if hasattr(results[0], 'to_json'):
            data = [record.to_json(join=False) for record in results]
        else:
            data = results
        if sys.stdout.isatty():
            Console().print(Syntax(json.dumps(data, indent=4), 'json',
                                   word_wrap=True, theme='solarized-dark',
                                   background_color='default'))
        else:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)

    def print_table(self, results: List[ModelInterface]) -> None:
        """Format records as an ASCII table."""
        if isinstance(results[0], list):
            # compound relationship (e.g., Recommendation.models)
            self.print_table([record for group in results for record in group])
            return
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

    @cached_property
    def field_selectors(self) -> List[FieldSelector]:
        """Build filter selections from arguments."""
        return [FieldSelector.from_cmdline(arg) for arg in self.filters]


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


def check_relation(target: ModelInterface, *path: str) -> Union[ModelInterface, Column]:
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


@dataclass
class FieldSelector:
    """Parse and prepare query filters based on command-line option."""

    name: str
    path: List[str]
    operand: str
    value: Any

    pattern = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)(\s*->\s*[a-zA-Z_][a-zA-Z0-9_]*)'
                         r'*\s*(==|!=|>|>=|<|<=|~)\s*(.*)$')
    op_call = {
        '==': lambda lhs, rhs: lhs == rhs,
        '!=': lambda lhs, rhs: lhs != rhs,
        '>=': lambda lhs, rhs: lhs >= rhs,
        '<=': lambda lhs, rhs: lhs <= rhs,
        '>':  lambda lhs, rhs: lhs > rhs,
        '<':  lambda lhs, rhs: lhs < rhs,
        '~':  lambda lhs, rhs: lhs.regexp_match(rhs),
    }

    def compile(self, model: ModelInterface) -> BinaryExpression:
        """Build binary expression object out of elements."""
        entity = getattr(model, self.name)
        for element in self.path:
            entity = entity[element]
        value = self.value if not self.path else type_coerce(self.value, JSON)
        return self.op_call[self.operand](entity, value)

    @classmethod
    def from_cmdline(cls, argument: str) -> FieldSelector:
        """
        Construct from command-line `argument`.

        Examaple:
            >>> FieldSelector.from_cmdline('a -> b == 42')
            FieldSelector(name='a', path=['b'], operand='==', value=42)
        """
        match = cls.pattern.match(argument)
        if match:
            name, path, operand, value = match.groups()
            path = [] if not path else [p.strip() for p in path.strip().split('->') if p.strip()]
            return FieldSelector(name=name, path=path, operand=operand, value=_typed(value))
        else:
            raise ArgumentError(f'Field selector not understood ({argument})')


def query_table(__name: str, limit: int = None, count: bool = False,
                filters: List[FieldSelector] = None) -> Union[List[ModelInterface], int]:
    """Query a given table by `__name` with `filters`."""
    session = Session()
    query = session.query(tables[__name])
    for selector in filters:
        query = query.filter(selector.compile(tables[__name]))
    if count is True:
        return query.count()
    if limit is not None:
        query = query.limit(limit)
    return query.all()
