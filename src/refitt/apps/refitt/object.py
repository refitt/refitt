# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Query database for info on an object."""


# type annotations
from __future__ import annotations
from typing import Callable, Dict

# standard libs
import sys
import json
from functools import partial, cached_property

# external libs
import yaml
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from rich.console import Console
from rich.syntax import Syntax

# internal libs
from refitt.core.exceptions import handle_exception
from refitt.core.logging import Logger
from refitt.database.model import Object

# public interface
__all__ = ['QueryObjectApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt object'
USAGE = f"""\
usage: {PROGRAM} [-h] NAME [--json]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
NAME                   Object name.

options:
    --json             Format output as JSON.
-h, --help             Show this message and exit.\
"""


class QueryObjectApp(Application):
    """Application class for object query entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    name: str
    interface.add_argument('name')

    format_json: bool = False
    interface.add_argument('--json', action='store_true', dest='format_json')

    include_data: bool = False
    interface.add_argument('-d', '--data', action='store_true', dest='include_data')

    include_history: bool = False
    interface.add_argument('-l', '--history', action='store_true', dest='include_history')

    exceptions = {
        Object.NotFound: partial(handle_exception, logger=log, status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Business logic of command."""
        info = self.load_object().to_json()
        if not self.include_data:
            info.pop('data')
        if not self.include_history:
            info.pop('history')
        self.write(info)

    def load_object(self) -> Object:
        """Load object from database."""
        if self.name.isdigit():
            return Object.from_id(int(self.name))
        else:
            return Object.from_name(self.name)

    def write(self, data: dict) -> None:
        """Format and print `data` to console."""
        formatter = self.format_method[self.format_name]
        output = formatter(data)
        if sys.stdout.isatty():
            output = Syntax(output, self.format_name, word_wrap=True,
                            theme='solarized-dark', background_color='default')
            Console().print(output)
        else:
            print(output, file=sys.stdout, flush=True)

    @cached_property
    def format_name(self) -> str:
        """Either 'json' or 'yaml'."""
        return 'yaml' if not self.format_json else 'json'

    @cached_property
    def format_method(self) -> Dict[str, Callable[[dict], str]]:
        """Format data method."""
        return {
            'yaml': partial(yaml.dump, indent=4, sort_keys=False),
            'json': partial(json.dumps, indent=4),
        }
