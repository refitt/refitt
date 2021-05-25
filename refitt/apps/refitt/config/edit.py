# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Edit configuration file."""


# type annotations
from __future__ import annotations

# standard libs
import os
import logging
from subprocess import run

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from ....core.config import SITE, PATH

# public interface
__all__ = ['EditConfigApp', ]


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
