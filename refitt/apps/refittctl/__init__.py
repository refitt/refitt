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

"""Manage the REFITT daemon."""

# type annotations
from __future__ import annotations

# standard libs
import sys
import functools
import subprocess

# internal libs
from ..refittd.client import RefittDaemonClient
from ...core.logging import Logger
from ...core.exceptions import log_and_exit
from ...__meta__ import (__appname__, __version__, __copyright__,
                         __developer__, __contact__, __website__)

# external libs
from cmdkit import logging as _cmdkit_logging
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from logalpha.colors import ANSI_RESET, Color


PROGRAM = f'{__appname__}ctl'
PADDING = ' ' * len(PROGRAM)

ACTIONS = ['start', 'stop', 'status', 'restart', 'reload']
ACTION_OPT = '{' + ' | '.join(ACTIONS) + '}'

USAGE = f"""\
usage: {PROGRAM} {ACTION_OPT}
       {PADDING} [--help] [--version]

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

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger(__name__)


# inject logger back into cmdkit library
_cmdkit_logging.log = log
Application.log_error = log.critical


# colors
ANSI_BOLD = '\033[1m'
ANSI_GREEN = Color.from_name('green').foreground
ANSI_RED = Color.from_name('red').foreground


def daemon_unavailable(exc: Exception) -> int:
    """The daemon refused the connection, likely not running."""
    log.critical('daemon refused connection - is it running?')
    return exit_status.runtime_error


class RefittController(Application):
    """Application class for the refitt service daemon, `refittd`."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('-v', '--version', version=__version__, action='version')

    action: str = None
    interface.add_argument('action', choices=ACTIONS)

    exceptions = {
        RuntimeError:
            functools.partial(log_and_exit, logger=log.critical,
                              status=exit_status.runtime_error),
        ConnectionRefusedError:
            daemon_unavailable,
    }

    def run(self) -> None:
        """Delegate action."""
        if self.action in ['start', 'status']:
            action = getattr(self, f'run_{self.action}')
            action()
        else:
            self.run_action()

    @staticmethod
    def run_start() -> None:
        """Start the daemon."""
        subprocess.run(['refittd', '--all', '--daemon'])

    @staticmethod
    def run_status() -> None:
        """Show the status of daemon services."""

        # retrieve status from daemon (returns dict)
        with RefittDaemonClient() as daemon:
            info = daemon.status

        for service, status in info.items():
            alive = status.pop('alive')
            color = ANSI_GREEN if alive else ANSI_RED
            state = 'alive' if alive else 'dead'
            pid = status.pop('pid')
            print(f'{color}● {service}: {state} ({pid}){ANSI_RESET}')
            for key, value in status.items():
                print(f'{key:>10}: {value}')

    def run_action(self) -> None:
        """Run the action."""
        with RefittDaemonClient() as daemon:
            daemon.request(self.action)

def main() -> int:
    """Entry-point for `refittctl` console application."""
    return RefittController.main(sys.argv[1:])
