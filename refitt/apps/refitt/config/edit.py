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

"""Edit configuration file."""

# type annotations
from __future__ import annotations

# standard libs
import os
import functools
import subprocess

# internal libs
from ....core.config import get_site, init_config
from ....core.exceptions import log_and_exit
from ....core.logging import Logger
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
PROGRAM = f'{__appname__} config edit'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{--system | --user | --site}} [--help]
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

The EDITOR environment variable must be set.

options:
    --system         Edit system configuration.
    --user           Edit user configuration.
    --site           Edit local configuration.
-h, --help           Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger(__name__)


class Edit(Application):
    """Edit configuration file."""

    interface = Interface(PROGRAM, USAGE, HELP)

    site: bool = False
    user: bool = False
    system: bool = False
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--site', action='store_true')
    site_interface.add_argument('--user', action='store_true')
    site_interface.add_argument('--system', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Open editor for configuration."""

        site = None
        config_path = None
        for key in ('site', 'user', 'system'):
            if getattr(self, key) is True:
                config_path = get_site(key)['cfg']
                site = key

        if not os.path.exists(config_path):
            log.info(f'{config_path} does not exist - initializing')
            init_config(site)

        if 'EDITOR' not in os.environ:
            raise RuntimeError('EDITOR must be set')

        editor = os.environ['EDITOR']
        subprocess.run([editor, config_path])
