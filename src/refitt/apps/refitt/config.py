# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Manage configuration."""


# type annotations
from __future__ import annotations
from typing import Any

# standard libs
import os
import sys
import json
import logging
import functools
import subprocess

# external libs
import toml
from cmdkit.app import Application, ApplicationGroup, exit_status
from cmdkit.cli import Interface, ArgumentError
from cmdkit.config import ConfigurationError
from rich.console import Console
from rich.syntax import Syntax

# internal libs
from refitt.core.platform import path
from refitt.core.typing import coerce as coerce_type
from refitt.core.config import load_file, update, config as full_config
from refitt.core.exceptions import handle_exception

# public interface
__all__ = ['ConfigApp', ]

# module logger
log = logging.getLogger(__name__)


EDIT_PROGRAM = 'refitt config edit'
EDIT_USAGE = f"""\
usage: {EDIT_PROGRAM} [-h] [--system | --user]
Edit configuration with default editor.\
"""

EDIT_HELP = f"""\
{EDIT_USAGE}

The EDITOR/VISUAL environment variable must be set.

options:
    --system         Edit system configuration.
    --user           Edit user configuration (default).
-h, --help           Show this message and exit.\
"""


class ConfigEditApp(Application):
    """Edit configuration with default editor."""

    interface = Interface(EDIT_PROGRAM, EDIT_USAGE, EDIT_HELP)

    site_name: str = 'user'
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--user', action='store_const', const='user')
    site_interface.add_argument('--system', action='store_const', const='system')

    def run(self) -> None:
        """Business logic for `config edit`."""

        config_path = path[self.site_name].config
        editor = os.getenv('EDITOR', os.getenv('VISUAL', None))
        if not editor:
            raise RuntimeError('EDITOR or VISUAL environment variable not defined')

        log.debug(f'Opening {config_path}')
        log.debug(f'Editor: {editor}')
        subprocess.run([editor, config_path])


GET_PROGRAM = 'refitt config get'
GET_USAGE = f"""\
usage: {GET_PROGRAM} [-h] [-x] SECTION[...].VAR [--system | --user]
Get configuration option.\
"""

GET_HELP = f"""\
{GET_USAGE}

If --user/--system not specified, the output is the merged configuration
from all sources. Use `refitt config which` to see where a specific
option originates from.

arguments:
SECTION[...].VAR          Path to variable.

options:
    --system              Load from system configuration.
    --user                Load from user configuration.
-x, --expand              Expand variable.
-h, --help                Show this message and exit.\
"""


class ConfigGetApp(Application):
    """Get configuration option."""

    interface = Interface(GET_PROGRAM, GET_USAGE, GET_HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    site_name: str = None
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--user', action='store_const', const='user', dest='site_name')
    site_interface.add_argument('--system', action='store_const', const='system', dest='site_name')

    expand: bool = False
    interface.add_argument('-x', '--expand', action='store_true')

    exceptions = {
        ConfigurationError: functools.partial(handle_exception, logger=log, status=exit_status.bad_config),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Business logic for `config get`."""

        if self.site_name is None:
            config_path = 'configuration'  # Note: not meaningful for merged configuration
            config = full_config
        else:
            config_path = path[self.site_name].config
            if os.path.exists(config_path):
                config = load_file(config_path)
            else:
                raise ConfigurationError(f'{config_path} does not exist')

        if self.varpath == '.':
            self.print_output(config)
            return

        if '.' not in self.varpath:
            if self.varpath in config:
                self.print_output(config[self.varpath])
                return
            else:
                raise ConfigurationError(f'"{self.varpath}" not found in {config_path}')

        if self.varpath.startswith('.'):
            raise ConfigurationError(f'Section name cannot start with "."')

        section, *subsections, variable = self.varpath.split('.')
        if section not in config:
            raise ConfigurationError(f'"{section}" is not a section in {config_path}')

        config_section = config[section]
        if subsections:
            subpath = f'{section}'
            try:
                for subsection in subsections:
                    subpath += f'.{subsection}'
                    if not isinstance(config_section[subsection], dict):
                        raise ConfigurationError(f'"{subpath}" not a section in {config_path}')
                    else:
                        config_section = config_section[subsection]
            except KeyError as error:
                raise ConfigurationError(f'"{subpath}" not found in {config_path}') from error

        if self.expand:
            try:
                value = getattr(config_section, variable)
            except AttributeError as error:
                raise ConfigurationError('') from error
            if value is None:
                raise ConfigurationError(f'"{variable}" not found in {config_path}')
            self.print_output(value)
            return
        elif variable in config_section:
            self.print_output(config_section[variable])
        else:
            raise ConfigurationError(f'"{self.varpath}" not found in {config_path}')

    def print_output(self, value: Any) -> None:
        """Format and print final `value`."""
        value = self.format_output(value)
        if sys.stdout.isatty():
            output = Syntax(value, 'toml', word_wrap=True,
                            theme = full_config.console.theme,
                            background_color = 'default')
            Console().print(output)
        else:
            print(value, file=sys.stdout, flush=True)

    def format_output(self, value: Any) -> str:
        """Format `value` as appropriate text."""
        if isinstance(value, dict):
            value = self.format_section(value)
        else:
            value = json.dumps(value)  # NOTE: close enough
        return value

    def format_section(self, value: dict) -> str:
        """Format an entire section for output."""
        if self.varpath == '.':
            value = toml.dumps(value)
        else:
            value = toml.dumps({self.varpath: value})
        # NOTE: Fix weird formatting of section headings.
        #       The `toml.dumps` output has unnecessary quoting.
        lines = []
        for line in value.strip().split('\n'):
            if not line.startswith('['):
                lines.append(line)
            else:
                lines.append(line.replace('"', ''))
        value = '\n'.join(lines)
        return value


SET_PROGRAM = 'refitt config set'
SET_USAGE = f"""\
usage: {SET_PROGRAM} [-h] SECTION[...].VAR VALUE [--system | --user]
Set configuration option.\
"""

SET_HELP = f"""\
{SET_USAGE}

arguments:
SECTION[...].VAR        Path to variable.
VALUE                   Value to be set.

options:
    --system            Apply to system configuration.
    --user              Apply to user configuration (default).
-h, --help              Show this message and exit.\
"""


class ConfigSetApp(Application):
    """Set configuration option."""

    interface = Interface(SET_PROGRAM, SET_USAGE, SET_HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    value: str = None
    interface.add_argument('value', type=coerce_type)

    site_name: str = 'user'
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--user', action='store_const', const='user', dest='site_name', default=site_name)
    site_interface.add_argument('--system', action='store_const', const='system', dest='site_name')

    def run(self) -> None:
        """Business logic for `config set`."""

        if '.' not in self.varpath:
            raise ArgumentError('Missing section in variable path')

        section, *subsections, variable = self.varpath.split('.')

        config = {section: {}}
        config_section = config[section]
        for subsection in subsections:
            if subsection not in config_section:
                config_section[subsection] = dict()
            config_section = config_section[subsection]

        config_section[variable] = self.value
        update(self.site_name, config)


WHICH_PROGRAM = 'refitt config which'
WHICH_USAGE = f"""\
usage: {WHICH_PROGRAM} [-h] SECTION[...].VAR
Show origin of configuration option.\
"""

WHICH_HELP = f"""\
{WHICH_USAGE}

arguments:
SECTION[...].VAR        Path to variable.

options:
-h, --help              Show this message and exit.\
"""


class ConfigWhichApp(Application):
    """Show origin of configuration option."""

    interface = Interface(WHICH_PROGRAM, WHICH_USAGE, WHICH_HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    def run(self) -> None:
        """Business logic for `config which`."""
        try:
            site = full_config.which(*self.varpath.split('.'))
        except KeyError:
            log.critical(f'"{self.varpath}" not found')
            return
        if site in ('default', 'env', 'logging', ):
            print(site)
        else:
            print(f'{site}: {path[site].config}')


SYSTEM_CONFIG_PATH = '/etc/refitt.toml'
USER_CONFIG_PATH = '~/.refitt/config.toml'


PROGRAM = 'refitt config'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
get                      {ConfigGetApp.__doc__}
set                      {ConfigSetApp.__doc__}
edit                     {ConfigEditApp.__doc__}
which                    {ConfigWhichApp.__doc__}

options:
-h, --help               Show this message and exit.

files:
  (system)  {SYSTEM_CONFIG_PATH}
    (user)  {USER_CONFIG_PATH}
"""


class ConfigApp(ApplicationGroup):
    """Manage configuration."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'get': ConfigGetApp,
                'set': ConfigSetApp,
                'edit': ConfigEditApp,
                'which': ConfigWhichApp, }
