# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Make authenticated REFITT API requests."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Callable, Optional, IO, Any, Union, Final

# standard libs
import os
import sys
import json
import functools
from io import BytesIO
from functools import cached_property

# external libs
import yaml
from requests.exceptions import ConnectionError
from cmdkit.app import Application, ApplicationGroup, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax

# internal libs
from refitt.core import typing, ansi, __version__
from refitt.core.exceptions import handle_exception
from refitt.core.logging import Logger
from refitt.core.config import config
from refitt.core.web import request
from refitt.core.web.response import STATUS_CODE

# public interface
__all__ = ['RequestApp', ]

# application logger
log = Logger.with_name(__name__)


PROGRAM = 'refitt-client'
PADDING = ' ' * len(PROGRAM)

LOGIN_PROGRAM: Final[str] = f'{PROGRAM} login'
LOGIN_USAGE: Final[str] = f"""\
Usage:
  {LOGIN_PROGRAM} [-h] [--force]
  Fetch and store client key and secret.\
"""

LOGIN_HELP: Final[str] = f"""\
{LOGIN_USAGE}

  Login will not occur if credentials already exist in your
  configuration file. Use -f/--force to ignore this criterion.

Options:
  -f, --force           Force creation of new secret.
  -h, --help            Show this message and exit.\
"""


class Login(Application):
    """Fetch and store client key and secret."""

    interface = Interface(LOGIN_PROGRAM, LOGIN_USAGE, LOGIN_HELP)
    ALLOW_NOARGS = True

    force: bool = False
    interface.add_argument('-f', '--force', action='store_true')

    def run(self) -> None:
        """Run login method."""
        if self.force:
            request.login(force=True)
            return
        try:
            getattr(config.api, 'key')
            getattr(config.api, 'secret')
        except AttributeError:
            request.login()
        else:
            log.info('Already logged in, use -f/--force to get new credentials')


WHOAMI_PROGRAM: Final[str] = f'{PROGRAM} whoami'
WHOAMI_USAGE: Final[str] = f"""\
Usage:
  {WHOAMI_PROGRAM} [-h]
  Verify credentials with server and return user profile.\
"""

WHOAMI_HELP: Final[str] = f"""\
{WHOAMI_USAGE}

Options:
  -h, --help            Show this message and exit.\
"""


class WhoAmI(Application):
    """Verify credentials with server and return user profile."""

    interface = Interface(WHOAMI_PROGRAM, WHOAMI_USAGE, WHOAMI_HELP)
    interface.add_argument('-v', '--version', action='version', version=__version__)
    ALLOW_NOARGS = True

    exceptions = {
        ConnectionError: functools.partial(handle_exception, logger=log,
                                           status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Make web request."""
        try:
            self.apply_settings()
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
        return request.get('whoami', extract_response=False, raise_on_error=True)

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

    @staticmethod
    def apply_settings() -> None:
        """Additional setup requirements before making web request."""
        request.PERSIST_TOKEN = True


DESCRIBE_PROGRAM: Final[str] = f'{PROGRAM} describe'
DESCRIBE_USAGE: Final[str] = f"""\
Usage:
  {DESCRIBE_PROGRAM} [-h] [ROUTE]
  Fetch descriptions of API endpoints.\
"""

DESCRIBE_HELP: Final[str] = f"""\
{DESCRIBE_USAGE}

  If no ROUTE is given, return all routes.
  Formatted as YAML, for JSON call `{PROGRAM} get info`.

Arguments:
  ROUTE                 Specific top-level route (optional)
  
Options:
  -h, --help            Show this message and exit.\
"""


class Describe(Application):
    """Fetch descriptions of API endpoints."""

    interface = Interface(DESCRIBE_PROGRAM, DESCRIBE_USAGE, DESCRIBE_HELP)
    interface.add_argument('-v', '--version', action='version', version=__version__)
    ALLOW_NOARGS = True

    route: str = None
    interface.add_argument('route', nargs='?', default=route)

    exceptions = {
        ConnectionError: functools.partial(handle_exception, logger=log,
                                           status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Make web request."""
        try:
            self.apply_settings()
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
        """Issue request."""
        return request.get('info', extract_response=False, raise_on_error=True)

    def format_output(self, status: int, headers: dict, content: dict) -> None:
        """Format and print response data from request."""
        content = content['Response']
        if self.route:
            if self.route in content:
                content = content.get(self.route)
            else:
                log.critical(f'Unknown route: {self.route}')
                log.info(f'Use any of {", ".join(list(content.keys()))}')
        # Strip down info for brevity
        else:
            content = {
                name: {
                    route_path: {
                        method: route_info[method]['Description']
                        for method in route_info
                    }
                    for route_path, route_info in section['Endpoints'].items()
                }
                for name, section in content.items()
            }
        content = yaml.dump(content, indent=4)
        if sys.stdout.isatty():
            Console().print(Syntax(content, 'yaml',
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

    @staticmethod
    def apply_settings() -> None:
        """Additional setup requirements before making web request."""
        request.PERSIST_TOKEN = True


REQUEST_USAGE: Final[str] = f"""\
Usage: 
  {PROGRAM} {{get|put|post|delete}} <route> [<options>...] 
  {PADDING} [[-d DATA | @FILE] | [-f FILE]]
  {PADDING} [-r] [-x NODE] [--no-headers] [--download] [--admin [TOKEN]]

  {__doc__}\
"""

REQUEST_HELP: Final[str] = f"""\
{REQUEST_USAGE}

  For POST requests, include JSON payloads with -d/--data inline or with @ 
  preceded by a local file path. To upload a raw file as an attachment 
  use -f/--file.

  Downloaded files are not dumped with a live TTY but will be otherwise.
  Use --download to save to the local filesystem.

  Headers are displayed along with syntax highlighting if a TTY is detected.
  Extract a member element from JSON responses with -x/--extract 
  (e.g., '-x .Response.object').
  
  Strip quotations for extracted string literals with -r/--raw.

  URL parameters can be encoded inline, e.g.,
  > {PROGRAM} get recommendation limit==1 join==true

Arguments:
  method                         HTTP method (e.g., GET/PUT/POST/DELETE).
  route                          URL path (e.g., /object/1).
  options...                     URL parameters (e.g., 'limit==1').

Options:
  -d, --data       DATA | @FILE  Raw inline content or file path.
  -f, --file       FILE          Path to file for attachment. ('-' for stdin).
  -x, --extract    NODE          JSON path for element (e.g., '.Response.user').
  -r, --raw                      Strip quotes on single extracted string literal.
      --no-headers               Do now show headers for TTY.
      --download                 Save file attachment.
      --admin      TOKEN         Use alternate token (or use `config.api.admin_token`).
"""


class RequestApp(Application):
    """Make authenticated request."""

    # overriden by subclasses
    method: str

    interface = Interface(PROGRAM, REQUEST_USAGE, REQUEST_HELP)
    interface.add_argument('-v', '--version', action='version', version=__version__)

    route: str = None
    interface.add_argument('route')

    options: List[str] = None
    interface.add_argument('options', nargs='*', default=[])

    token: str = None
    admin_token: str = None
    interface.add_argument('--admin', action='store_const', const=True, dest='admin_token')

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
        ConnectionError: functools.partial(handle_exception, logger=log, status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Make web request."""
        self.check_args()
        self.apply_settings()
        try:
            if not self.admin_token:
                self.format_output(**self.make_request())
            else:
                token = self.admin_token if isinstance(self.admin_token, str) else config.api.admin_token
                with request.use_token(token):
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
        if self.route.strip('/') == 'token':
            log.warning('Calling /token is not necessary with refitt-client')
        if self.route.strip('/').startswith('client'):
            log.warning('Use `refitt-client login` subcommand instead')
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
        if method in ('get', 'put', 'delete', 'post'):
            return getattr(request, method)
        else:
            raise ArgumentError(f'Method not supported \'{method}\'')

    @property
    def endpoint(self) -> Callable[..., dict]:
        """Bound method from `refitt.core.web.request` called with the `route`."""
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
        return self.endpoint(extract_response=False, raise_on_error=True,
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
            self.format_octet_stream(content)
        else:
            self.format_json(content)

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

    def format_octet_stream(self, content: dict) -> None:
        """Format output and save file to local disk if needed."""
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

    def format_json(self, content: dict) -> None:
        """Format output for JSON content."""
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


class Get(RequestApp):
    """GET request."""
    method: str = 'get'


class Put(RequestApp):
    """PUT request."""
    method: str = 'put'


class Post(RequestApp):
    """POST request."""
    method: str = 'post'


class Delete(RequestApp):
    """DELETE request."""
    method: str = 'delete'


CLIENT_USAGE: Final[str] = f"""\
Usage:
  {PROGRAM} [-h] [-v] <command> [<args>...]
  {__doc__}\
"""

CLIENT_HELP: Final[str] = f"""\
{CLIENT_USAGE}

Commands:
  login                 {Login.__doc__}
  whoami                {WhoAmI.__doc__}
  describe              {Describe.__doc__}
  get                   {Get.__doc__}
  put                   {Put.__doc__}
  post                  {Post.__doc__}
  delete                {Delete.__doc__}

Options:
  -v, --version         Show the version and exit.     
  -h, --help            Show this message and exit.\
"""


class ClientApp(ApplicationGroup):
    """Application group for refitt-client."""

    interface = Interface(PROGRAM, CLIENT_USAGE, CLIENT_HELP)
    interface.add_argument('command')
    interface.add_argument('-v', '--version', action='version', version=__version__)

    command = None
    commands = {'login': Login,
                'whoami': WhoAmI,
                'describe': Describe,
                'get': Get,
                'put': Put,
                'post': Post,
                'delete': Delete,
                }


def main(argv: List[str] = None) -> int:
    return ClientApp.main(sys.argv[1:])
