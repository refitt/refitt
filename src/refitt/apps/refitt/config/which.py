# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Check origin of configuration variable."""


# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from refitt.core.config import config
from refitt.core.platform import path
from refitt.core.logging import Logger

# public interface
__all__ = ['WhichConfigApp', ]

# application logger
log = Logger.with_name('refitt')


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
            print(f'{site}: {path[site].config}')
