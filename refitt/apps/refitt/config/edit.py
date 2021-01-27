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
import logging
from functools import partial
from subprocess import run


# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface

# internal libs
from ....core.config import SITE, PATH, ConfigurationError
from ....core.exceptions import log_exception


PROGRAM = 'refitt config edit'
USAGE = f"""\
usage: {PROGRAM} [-h] [--system | --user | --local]
{__doc__}\
"""

HELP = f"""\
{USAGE}

The EDITOR environment variable must be set.

options:
    --system         Edit system configuration.
    --user           Edit user configuration.
    --site           Edit local configuration.
-h, --help           Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class EditConfigApp(Application):
    """Application class for config edit command."""

    interface = Interface(PROGRAM, USAGE, HELP)

    local: bool = False
    user: bool = False
    system: bool = False
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--local', action='store_true')
    site_interface.add_argument('--user', action='store_true')
    site_interface.add_argument('--system', action='store_true')

    exceptions = {
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        ConfigurationError: partial(log_exception, logger=log.critical,
                                    status=exit_status.bad_config),
    }

    def run(self) -> None:
        """Open editor for configuration."""
        site = SITE
        path = PATH[site].config
        for key in ('local', 'user', 'system'):
            if getattr(self, key) is True:
                site = key
                path = PATH[site].config

        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

        if 'EDITOR' not in os.environ:
            raise RuntimeError('EDITOR must be set')

        editor = os.environ['EDITOR']
        run([editor, path])
