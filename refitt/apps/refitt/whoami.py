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

"""Check authentication and show user profile."""


# type annotations
from __future__ import annotations

# standard libs
import sys
import json
import functools
import logging

# internal libs
from ...web import request
from ...web.api.response import STATUS_CODE
from ...core.exceptions import log_exception
from ...core import ansi

# external libs
from requests.exceptions import ConnectionError
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from rich.console import Console
from rich.syntax import Syntax


PROGRAM = 'refitt whoami'
USAGE = f"""\
usage: {PROGRAM} [-h]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-h, --help            Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class WhoAmIApp(Application):
    """Application class for /whoami api call."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.error,
                                        status=exit_status.runtime_error),
        ConnectionError: functools.partial(log_exception, logger=log.error,
                                           status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Make web request."""
        try:
            self.format_output(**self.make_request())
        except request.APIError as error:
            response, = error.args
            self.format_output(**{
                'status': response.status_code,
                'headers': {'Protocol': request.get_protocol(response),
                            'Version': request.get_protocol_version(response),
                            **response.headers},
                'content': response.json()
            })

    @staticmethod
    def make_request() -> dict:
        """Issue web request."""
        return request.get('whoami', extract_response=False, raise_on_error=False)

    def format_output(self, status: int, headers: dict, content: dict) -> None:
        """Format and print response data from request."""
        content = json.dumps(content, indent=4)
        if sys.stdout.isatty():
            self.format_headers(status, headers)
            Console().print(Syntax(content, 'json',
                                   word_wrap=True, theme='solarized-dark',
                                   background_color='default'))
        else:
            print(content)

    @staticmethod
    def format_headers(status: int, headers: dict) -> None:
        """Display request info and headers."""
        headers.pop('Connection', None)
        protocol = headers.pop('Protocol')
        version = headers.pop('Version')
        print(f'{ansi.blue(protocol)}/{ansi.blue(version)} {ansi.cyan(str(status))} '
              f'{ansi.cyan(STATUS_CODE[status])}')
        for field, value in headers.items():
            print(f'{ansi.cyan(field)}: {value}')
