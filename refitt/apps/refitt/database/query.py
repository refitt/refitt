# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Query database for records."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Type, Union, TypeVar, Any

# standard libs
import re
import sys
import json
import logging
from abc import ABC, abstractmethod, abstractproperty
from datetime import datetime
from functools import partial, cached_property
from dataclasses import dataclass

# external libs
from sqlalchemy import Column, type_coerce
from sqlalchemy.exc import InvalidRequestError, ProgrammingError, DataError
from sqlalchemy.types import JSON
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.query import Query
from sqlalchemy.engine.row import Row
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from pandas import DataFrame

# internal libs
from ....core.exceptions import log_exception
from ....database.model import ModelInterface, tables
from ....database.interface import Session

# public interface
__all__ = ['QueryDatabaseApp', ]


PROGRAM = 'refitt database query'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} [-h] ENTITY[.RELATION | ENTITY...] [-w COND [COND...]] 
       {PADDING} [--count | --limit NUM] [-s ENTITY] [-x] [ --json | --csv] [--dry-run] 
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
ENTITY[.RELATION ...]        Table name with relationship path.

options:
-w, --where           COND   Expressions to filter on (e.g., `user_id==2`).
    --json                   Format output as JSON.
    --csv                    Format output as CSV.
-x, --extract-values         Print values only (no formatting).
-c, --count                  Print row count.
-l, --limit                  Limit number of returned rows.
-s, --order-by       ENTITY  Sort results by specified column.
    --dry-run                Show SQL query, do not execute.
-h, --help                   Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class QueryDatabaseApp(Application):
    """Application class for database query entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    targets: List[str] = []
    interface.add_argument('targets', nargs='+')

    filters: List[str] = []
    interface.add_argument('-w', '--where', nargs='*', default=[], dest='filters')

    limit: int = None
    interface.add_argument('-l', '--limit', type=int, default=limit)

    order_by: str = None
    interface.add_argument('-s', '--order-by', default=None)

    show_count: bool = False
    interface.add_argument('-c', '--count', dest='show_count', action='store_true')

    format_csv: bool = False
    format_json: bool = False
    format_interface = interface.add_mutually_exclusive_group()
    format_interface.add_argument('--csv', action='store_true', dest='format_csv')
    format_interface.add_argument('--json', action='store_true', dest='format_json')

    dry_run: bool = False
    interface.add_argument('--dry-run', action='store_true')

    extract_values: bool = False
    interface.add_argument('-x', '--extract-values', action='store_true')

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
        self.check_arguments()
        selector = Selector.factory(self.targets)
        query = self.build_query(selector, filters=self.build_filters(selector))
        if self.dry_run:
            print(query)
        elif self.show_count:
            print(query.count())
        else:
            self.print_output(selector, query.all(), extract_values=self.extract_values)

    def build_query(self, selector: Selector, filters: List[FieldSelector]) -> Query:
        """Build query instance via `selector` implementation and apply `filters`."""
        query = selector.query()
        if self.order_by:
            arg = self.order_by
            pattern = re.compile(r'^[a-z_]+\.')
            default_name = selector.model.__tablename__
            field = EntityRelation.from_arg(arg if pattern.match(arg) else f'{default_name}.{arg}')
            query = query.order_by(field.select())
        for cond in filters:
            query = query.filter(cond.compile())
        if self.limit is not None:
            query = query.limit(self.limit)
        return query

    def build_filters(self, selector: Selector) -> List[FieldSelector]:
        """Create list of field selectors from command-line arguments."""
        pattern = re.compile(r'^[a-z_]+\.')
        default_name = selector.model.__tablename__
        return [FieldSelector.from_cmdline(arg if pattern.match(arg) else f'{default_name}.{arg}')
                for arg in self.filters]

    def check_arguments(self) -> None:
        """Logic check on command-line arguments."""
        if (len(self.targets) > 1 or '.' not in self.targets[0]) and self.extract_values:
            raise ArgumentError('Cannot extract values for multiple columns')

    @cached_property
    def output_format(self) -> str:
        """Either 'table', 'csv', or 'json'."""
        for ftype in 'csv', 'json':
            if getattr(self, f'format_{ftype}'):
                return ftype
        else:
            return 'table'

    def print_output(self, selector: Selector, *args, **kwargs) -> None:
        return getattr(selector, f'print_{self.output_format}')(*args, **kwargs)


RT = TypeVar('RT', ModelInterface, Row)
Result = Union[ModelInterface, Tuple[RT, ...]]


@dataclass
class Selector(ABC):
    """Common interface for all selectors."""

    entities: List[EntityRelation]

    @classmethod
    def from_args(cls, args: List[str]) -> Selector:
        """Build entities first from arguments."""
        return cls([EntityRelation.from_arg(arg) for arg in args])

    @abstractproperty
    def model(self) -> Type[ModelInterface]:
        """The primary model interface for the selector."""

    @abstractmethod
    def query(self) -> Query:
        """Build initial query from selector entities."""

    @abstractmethod
    def print_table(self, results: List[Result], extract_values: bool = False) -> None:
        """Print results in table format."""

    @abstractmethod
    def print_json(self, results: List[Result], extract_values: bool = False) -> None:
        """Print results in JSON format."""

    @abstractmethod
    def print_csv(self, results: List[Result], extract_values: bool = False) -> None:
        """Print results in CSV format."""

    @classmethod
    def factory(cls, args: List[str]) -> Selector:
        """Choose selector implementation based on pattern in entities."""
        if len(args) == 1:
            if '.' not in args[0]:
                return SimpleTableSelector.from_args(args)
            else:
                entity = EntityRelation.from_arg(args[0])
                if len(entity.path) > 1 or entity.path[0] in entity.model.relationships:
                    return SingleCompoundSelector.from_args(args)
                else:
                    return SimpleColumnSelector.from_args(args)
        else:
            return SimpleColumnSelector.from_args(args)


@dataclass
class SimpleTableSelector(Selector):
    """A simple table selector."""

    @property
    def model(self) -> Type[ModelInterface]:
        return self.entities[0].model

    def query(self) -> Query:
        """Query a single table."""
        return Session.query(self.model)

    def print_table(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in table format from simple instances of ModelInterface."""
        entity = self.entities[0]
        table = Table(title=None)
        table.add_column('id', justify='right', style='cyan')
        for name in list(entity.model.columns.keys())[1:]:
            table.add_column(name, justify='left')
        for record in results:
            table.add_row(*map(str, record.to_tuple()))
        Console().print(table)

    def print_json(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in JSON format from simple instances of ModelInterface."""
        data = [record.to_json(join=False) for record in results]
        if sys.stdout.isatty():
            Console().print(Syntax(json.dumps(data, indent=4), 'json',
                                   word_wrap=True, theme='solarized-dark',
                                   background_color='default'))
        else:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)

    def print_csv(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in CVS format from simple instances of ModelInterface."""
        fields = list(self.model.columns.keys())
        dataframe = DataFrame([row.to_tuple() for row in results], columns=fields)
        print(dataframe.to_csv(index=False))


@dataclass
class SimpleColumnSelector(Selector):
    """A simple column based selector."""

    @classmethod
    def from_args(cls, args: List[str]) -> Selector:
        """Auto-expand singular table names into all column names."""
        base = super().from_args(args)
        return cls([sub for entity in base.entities for sub in entity.expand()])

    @property
    def model(self) -> Type[ModelInterface]:
        return self.entities[0].model

    def query(self) -> Query:
        """Join additional tables if present."""
        query = Session.query(*[entity.select() for entity in self.entities])
        relationships = {model: name for name, model in self.model.relationships.items()}
        secondary_models = []
        for entity in self.entities[1:]:
            if entity.model is not self.model and entity.model not in secondary_models:
                secondary_models.append(entity.model)
                if entity.model in self.model.relationships.values():
                    query = query.join(entity.model, getattr(self.model, relationships.get(entity.model)))
                else:
                    raise ArgumentError(f'Entity `{entity.name}` does not relate to `{self.entities[0].name}`')
        return query

    def print_table(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in table format from rows."""
        if extract_values and len(results[0]) == 1:
            for row in results:
                value, = row
                print(value)
        else:
            table = Table(title=None)
            for entity in self.entities:
                field = f'{entity.name}.{entity.path[0]}'
                table.add_column(field, justify='left')
            for record in results:
                table.add_row(*map(str, record))
            Console().print(table)

    def print_json(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in JSON format from simple named tuples."""
        fields = [f'{entity.name}.{entity.path[0]}' for entity in self.entities]
        data = [{field: _pre_serialize(value) for field, value in zip(fields, record)} for record in results]
        if sys.stdout.isatty():
            Console().print(Syntax(json.dumps(data, indent=4), 'json',
                                   word_wrap=True, theme='solarized-dark',
                                   background_color='default'))
        else:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)

    def print_csv(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in CVS format from rows."""
        fields = [f'{entity.name}.{entity.path[0]}' for entity in self.entities]
        dataframe = DataFrame(results, columns=fields)
        print(dataframe.to_csv(index=False))


@dataclass
class SingleCompoundSelector(Selector):
    """A selector for traversing relations across tables."""

    @property
    def model(self) -> Type[ModelInterface]:
        return self.entities[0].model

    def query(self) -> Query:
        """
        Dynamically apply joining logic based on target entity specification.
        E.g., `observation.source.user.id` would automatically apply a compound
        join along source -> user by their common foreign keys.
        """
        parent = self.entities[0].model
        relationships = []
        for attr in self.entities[0].path:
            if hasattr(parent, 'relationships'):
                relationships.append(getattr(parent, attr))
                parent = parent.relationships.get(attr)
        query = Session.query(self.entities[0].model)
        if relationships:
            full_join = joinedload(relationships[0])
            for relationship in relationships[1:]:
                full_join = full_join.joinedload(relationship)
            query = query.options(full_join)
        return query

    def print_table(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in table format from instances of ModelInterface or rows."""
        entity = self.entities[0]
        for relation in entity.path:
            results = [getattr(record, relation) for record in results]
        table = Table(title=None)
        if isinstance(results[0], ModelInterface):
            table.add_column('id', justify='right', style='cyan')
            for name in list(results[0].columns.keys())[1:]:
                table.add_column(name, justify='left')
            for record in results:
                table.add_row(*map(str, record.to_tuple()))
            Console().print(table)
        else:
            if extract_values:
                for row in results:
                    print(row)
            else:
                table.add_column(f'{entity.name}.' + '.'.join(entity.path))
                for record in results:
                    table.add_row(str(record))
                Console().print(table)

    def print_json(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in JSON format from instances of ModelInterface or rows."""
        entity = self.entities[0]
        for relation in entity.path:
            results = [getattr(record, relation) for record in results]
        if isinstance(results[0], ModelInterface):
            data = [record.to_json(join=False) for record in results]
        else:
            data = [value for row in results for value in row]
        if sys.stdout.isatty():
            Console().print(Syntax(json.dumps(data, indent=4), 'json',
                                   word_wrap=True, theme='solarized-dark',
                                   background_color='default'))
        else:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)

    def print_csv(self, results: List[Result], extract_values: bool = False) -> None:
        """Print in CVS format from simple instances of ModelInterface or rows."""
        entity = self.entities[0]
        for relation in entity.path:
            results = [getattr(record, relation) for record in results]
        if isinstance(results[0], ModelInterface):
            data = [record.to_json(join=False) for record in results]
            dataframe = DataFrame(data, columns=list(results[0].columns.keys()))
            print(dataframe.to_csv(index=False))
        else:
            dataframe = DataFrame(results, columns=[f'{entity.name}.{entity.path[0]}', ])
            print(dataframe.to_csv(index=False, header=(not extract_values)))


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


def _pre_serialize(value: Any) -> Union[Any, str]:
    """Convert `value` to str if datetime, otherwise do nothing."""
    return value if not isinstance(value, datetime) else str(value)


def check_relation(model: Type[ModelInterface], *path: str) -> Union[Type[ModelInterface], Column]:
    """Validate we can actually select on the given relation `path`."""
    try:
        if not path:
            return model
        else:
            if hasattr(model, 'relationships') and path[0] in model.relationships:
                return check_relation(model.relationships[path[0]], *path[1:])
            else:
                return check_relation(getattr(model, path[0]), *path[1:])
    except AttributeError as error:
        raise ArgumentError(str(error)) from error


@dataclass
class EntityRelation:
    """Contains a parent table and member relation path."""

    name: str
    path: List[str]

    @classmethod
    def from_arg(cls, arg: str) -> EntityRelation:
        """Separate the left hand table name from its relation path."""
        name, *path = arg.split('.')
        if name in tables:
            check_relation(tables.get(name), *path)
            return cls(name, path)
        else:
            raise ArgumentError(f'Entity `{name}` does not name existing table')

    @property
    def model(self) -> Type[ModelInterface]:
        """The model interface for the named table."""
        return tables.get(self.name)

    def expand(self) -> List[EntityRelation]:
        """Expand an entity into one for each column if not already specific to a column."""
        return [self, ] if self.path else [EntityRelation(self.name, [column, ]) for column in self.model.columns]

    def select(self) -> Column:
        """Choose the member relation (i.e., column) for the named table."""
        if len(self.path) == 0:
            return self.model
        if len(self.path) == 1:
            return getattr(self.model, *self.path)
        else:
            raise NotImplementedError(f'Cannot select entity nested more than one layer deep, '
                                      f'`{self.name}{self.path}`')


@dataclass
class FieldSelector:
    """Parse and prepare query filters based on command-line argument."""

    parent: str
    name: str
    path: List[str]
    operand: str
    value: Any

    pattern = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
                         r'(\s*->\s*[a-zA-Z_][a-zA-Z0-9_]*)'
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

    @property
    def model(self) -> Type[ModelInterface]:
        return tables.get(self.parent)

    def compile(self) -> BinaryExpression:
        """Build binary expression object out of elements."""
        entity = getattr(self.model, self.name)
        for element in self.path:
            entity = entity[element]
        value = self.value if not self.path else type_coerce(self.value, JSON)
        return self.op_call[self.operand](entity, value)

    @classmethod
    def from_cmdline(cls, argument: str) -> FieldSelector:
        """
        Construct from command-line `argument`.

        Example:
            >>> FieldSelector.from_cmdline('object.aliases -> tag == foo_bar_baz')
            FieldSelector(parent='object', name='aliases', path=['tag'], operand='==', value='foo_bar_baz')
        """
        match = cls.pattern.match(argument)
        if match:
            parent, name, path, operand, value = match.groups()
            path = [] if not path else [p.strip() for p in path.strip().split('->') if p.strip()]
            return FieldSelector(parent=parent, name=name, path=path, operand=operand, value=_typed(value))
        else:
            raise ArgumentError(f'Field selector not understood ({argument})')
