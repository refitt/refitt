# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Check origin of configuration variable."""


# standard libs
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from ....core.config import PATH, config

# public interface
__all__ = ['WhichConfigApp', ]


PROGRAM = 'refitt config which'
USAGE = f"""\
usage: {PROGRAM} [-h] SECTION[...].VAR
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
SECTION[...].VAR        Path to variable.

options:
-h, --help              Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class WhichConfigApp(Application):
    """Application class for config which command."""

    interface = Interface(PROGRAM, USAGE, HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    def run(self) -> None:
        """Business logic for `config which`."""
        try:
            site = config.which(*self.varpath.split('.'))
        except KeyError:
            self.log_critical(f'"{self.varpath}" not found')
            return
        if site in ('default', 'env'):
            print(site)
        else:
            path = PATH[site].config
            print(f'{site}: {path}')
