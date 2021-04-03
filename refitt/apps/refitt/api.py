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
from typing import List, Dict, Callable, Optional, IO, Any, Union

# standard libs
import os
import sys
import json
import functools
import logging
from io import BytesIO
from functools import cached_property

# internal libs
from ...web import request
from ...web.api.response import STATUS_CODE
from ...core.exceptions import log_exception
from ...core import typing, ansi

# external libs
from requests.exceptions import ConnectionError
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax


PROGRAM = 'refitt api'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} [-h] <method> <route> [<options>...] [[-d DATA | @FILE] | [-f FILE]] [-r] [-x NODE]
       {PADDING} [--download] [--no-headers]
{__doc__}\
"""

HELP = f"""\
{USAGE}

For POST requests, include JSON payloads with -d/--data inline or with @ preceded by
a local file path. To upload a raw file as an attachment use -f/--file.

Downloaded files are not dumped with a live TTY but will be otherwise, use --download
to save to the local filesystem.

Headers are displayed along with syntax highlighting if a TTY is detected.
Extract a member element from JSON responses with -x/--extract (e.g., '-x .Response.object').
Strip quotations for extracted string literals with -r/--raw.

URL parameters can be encoded inline, e.g.,
> refitt api get recommendation limit==1 join==true

arguments:
method                         HTTP method (e.g., GET/PUT/POST/DELETE).
route                          URL path (e.g., /object/1).
options...                     URL parameters (e.g., 'limit==1').

options:
-d, --data       DATA | @FILE  Raw inline content or file path.
-f, --file       FILE          Path to file for attachment. ('-' for stdin).
-x, --extract    NODE          JSON path for element (e.g., '.Response.user').
-r, --raw                      Strip quotes on single extracted string literal.
    --no-headers               Do now show headers for TTY.
    --download                 Save file attachment.
-h, --help                     Show this message and exit.\
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

    show_headers: bool = True
    interface.add_argument('--no-headers', action='store_false', dest='show_headers')

    download: bool = True
    interface.add_argument('--download', action='store_true')

    data_source: Optional[str] = None
    file_source: Optional[str] = None
    post_interface = interface.add_mutually_exclusive_group()
    post_interface.add_argument('-d', '--data', default=file_source, dest='data_source')
    post_interface.add_argument('-f', '--file', default=file_source, dest='file_source')

    extraction_path: Optional[str] = None
    interface.add_argument('-x', '--extract', default=None, dest='extraction_path')

    display_raw: bool = False
    interface.add_argument('-r', '--raw', action='store_true', dest='display_raw')

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.error,
                                        status=exit_status.runtime_error),
        ConnectionError: functools.partial(log_exception, logger=log.error,
                                           status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Make web request."""
        self.check_args()
        self.apply_settings()
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

    def check_args(self):
        """Validate method, position arguments, etc."""
        if self.file_source is not None and self.method.lower() != 'post':
            raise ArgumentError(f'Cannot use -f/--file option for {self.method.upper()} request')
        elif self.data_source is not None and self.method.lower() != 'post':
            raise ArgumentError(f'Cannot use -d/--data option for {self.method.upper()} request')
        for option in self.options:
            if '==' not in option:
                raise ArgumentError(f'Positional arguments should have equality syntax, \'{option}\'')

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

    @cached_property
    def files(self) -> Optional[Dict[str, IO]]:
        """Prepared file stream."""
        if self.file_source is None:
            return None
        elif self.file_source == '-':
            return {'<stdin>': BytesIO(sys.stdin.buffer.read())}
        else:
            with open(self.file_source, mode='rb') as stream:
                return {os.path.basename(self.file_source): BytesIO(stream.read())}

    @cached_property
    def data(self) -> Optional[dict]:
        """Prepared JSON data."""
        if self.data_source is None:
            return None
        elif not self.data_source.startswith('@'):
            return json.loads(self.data_source)
        else:
            with open(self.data_source[1:], mode='r') as stream:
                return json.load(stream)

    @cached_property
    def payload(self) -> Dict[str, Union[Dict[str, Any], Dict[str, IO]]]:
        """Mapping of request parameter and data/stream for request payload."""
        if self.file_source:
            return {'files': self.files}
        elif self.data_source:
            return {'json': self.data}
        else:
            return {}

    def make_request(self) -> dict:
        """Issue web request."""
        return self.endpoint(extract_response=False, raise_on_error=False,
                             **self.payload, **self.structured_options)

    @property
    def structured_options(self) -> dict:
        """Parse `{option}=={value}` positional arguments into dictionary."""
        return {
            option: typing.coerce(value) for option, value in [
                arg.split('==') for arg in self.options
            ]
        }

    def format_output(self, status: int, headers: dict, content: dict) -> None:
        """Format and print response data from request."""
        if sys.stdout.isatty() and self.show_headers:
            self.format_headers(status, headers)
        if headers['Content-Type'] == 'application/octet-stream':
            if not self.download:
                if sys.stdout.isatty():
                    print('---')
                    print(f'{ansi.red("Content-Disabled")}: use --download to save file')
                else:
                    (filename, data), = content.items()
                    sys.stdout.buffer.write(data)
            else:
                (filename, data), = content.items()
                self.save_local(filename, data)
        else:
            if self.extraction_path is not None:
                content = self.extract_partial(content, self.extraction_path)
            if isinstance(content, (dict, list)):
                content = json.dumps(content, indent=4)
                if sys.stdout.isatty():
                    Console().print(Syntax(content, 'json',
                                           word_wrap=True, theme='solarized-dark',
                                           background_color='default'))
                else:
                    print(content)
            else:
                content = json.dumps(content, indent=4)  # formats special types
                if self.display_raw:
                    content = content.strip('"')
                print(content)

    @staticmethod
    def extract_partial(content: dict, path: str) -> Any:
        """Pull sections or values out of nested `content`."""
        result = dict(content)
        for section in path.strip('.').split('.'):
            try:
                result = result[section]
            except KeyError as error:
                raise RuntimeError(f'Element not found \'{path}\'') from error
        return result

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

    @staticmethod
    def save_local(filename: str, data: bytes) -> None:
        """Attempt to save `data` as local file to `filename` path."""
        name = filename.strip('./')  # NOTE: safe path (e.g., no ../)
        path = name
        suffix = 1
        while os.path.exists(path):
            path = f'{name}.{suffix}'
            suffix += 1
        print()
        print(f'Writing {len(data)} B to "{path}"')
        with open(path, mode='wb') as stream:
            stream.write(data)
            print('Done.')

    @staticmethod
    def apply_settings() -> None:
        """Additional setup requirements before making web request."""
        request.PERSIST_TOKEN = True
