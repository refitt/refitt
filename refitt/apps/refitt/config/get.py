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

"""Get variable from configuration file."""

# type annotations
from __future__ import annotations

# standard libs
import os
import functools

# internal libs
from ....core.config import get_site
from ....core.exceptions import log_and_exit
from ....core.logging import Logger
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
import toml


# program name is constructed from module file name
PROGRAM = f'{__appname__} config get'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <section>[...].<variable> [--system | --user] [--help]
{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

arguments:
section[...].variable        Path to variable.

options:
    --user                   Apply to user configuration.
    --system                 Apply to system configuration.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger.with_name('.'.join(PROGRAM.split()))


class Get(Application):
    """Get variable from configuration file."""

    interface = Interface(PROGRAM, USAGE, HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    user: bool = False
    system: bool = False
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--user', action='store_true')
    site_interface.add_argument('--system', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Run init task."""

        config_path = get_site()['cfg']
        for key in ('user', 'system'):
            if getattr(self, key) is True:
                config_path = get_site(key)['cfg']

        if not os.path.exists(config_path):
            raise RuntimeError(f'{config_path} does not exist')

        with open(config_path, mode='r') as config_file:
            config = toml.load(config_file)

        # parse variable specification
        if '.' not in self.varpath:
            raise ArgumentError('missing section in variable path')

        section, *subsections, variable = self.varpath.split('.')

        if section not in config:
            raise RuntimeError(f'"{section}" is not a section')

        config_section = config[section]
        if subsections:
            try:
                for subsection in subsections:
                    config_section = config_section[subsection]
            except KeyError:
                subpath = '.'.join(subsections)
                raise RuntimeError(f'{section}.{subpath} not found in {config_path}')

        if variable not in config_section:
            raise RuntimeError(f'"{self.varpath}" not found in {config_path}')

        value = config_section[variable]
        if isinstance(value, dict):
            value = toml.dumps({self.varpath: value})
            value = value.replace('["', '[').replace('"]', ']')
            # FIXME: why toml adds the quotes?!

        print(value, flush=True)
