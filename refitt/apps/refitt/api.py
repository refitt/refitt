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

"""Make authenticate requests to the API."""

# type annotations
from __future__ import annotations
from typing import List, Callable

# standard libs
import sys
import json
import functools
import logging

# internal libs
from ...web import request
from ...core.exceptions import log_exception
from ...core import typing

# external libs
from requests.exceptions import ConnectionError
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax


PROGRAM = 'refitt api'
USAGE = f"""\
usage: {PROGRAM} [-h] <method> <route> [<options>...] 
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-h, --help                   Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class WebApp(Application):
    """Application class for requests module."""

    interface = Interface(PROGRAM, USAGE, HELP)

    method: str = None
    interface.add_argument('method')

    route: str = None
    interface.add_argument('route')

    options: List[str] = None
    interface.add_argument('options', nargs='*', default=[])

    exceptions = {
        ConnectionError: functools.partial(log_exception, logger=log.error,
                                           status=exit_status.runtime_error),
        request.APIError: functools.partial(log_exception, logger=log.error,
                                            status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Make web request."""
        self.check_args()
        self.apply_settings()
        self.format_response(self.make_request())

    def check_args(self):
        """Validate method, position arguments, etc."""
        for option in self.options:
            if '==' not in option:
                raise ArgumentError(f'Positional arguments should have assignment syntax, \'{option}\'')

    @property
    def request_method(self) -> Callable[..., dict]:
        """Bound method of `request` module by accessing named `method`."""
        method = self.method.lower()
        try:
            return getattr(request, method)
        except AttributeError:
            raise ArgumentError(f'Method not supported \'{method}\'')

    @property
    def endpoint(self) -> Callable[..., dict]:
        """Bound method from `refitt.web.request` called with the `route`."""
        return functools.partial(self.request_method, self.route)

    def make_request(self) -> dict:
        """Issue web request."""
        data = None if self.request_method is not request.post else sys.stdin.read()
        return self.endpoint(data=data, **self.structured_options)

    @property
    def structured_options(self) -> dict:
        """Parse `{option}=={value}` positional arguments into dictionary."""
        return {
            option: typing.coerce(value) for option, value in [
                arg.split('==') for arg in self.options
            ]
        }

    @staticmethod
    def format_response(response: dict) -> None:
        """Format and print `response` from request."""
        content = json.dumps(response, indent=4)
        if sys.stdout.isatty():
            Console().print(Syntax(content, 'json',
                                   word_wrap=True, theme='monokai',
                                   background_color='default'))
        else:
            print(content)

    @staticmethod
    def apply_settings() -> None:
        """Additional setup requirements before making web request."""
        request.PERSIST_TOKEN = True
