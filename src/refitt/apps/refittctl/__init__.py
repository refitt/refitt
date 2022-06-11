# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Refitt daemon controller."""


# type annotations
from __future__ import annotations

# standard libs
import sys
import functools
import subprocess

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
# from streamkit.core.logging import _ANSI_RESET, _ANSI_CODES  # noqa: protected-members

# internal lib
from refitt import __version__, __developer__, __contact__, __website__, __copyright__
from refitt.core import ansi
from refitt.core.exceptions import handle_exception, write_traceback
from refitt.core.logging import Logger
from refitt.daemon.client import DaemonClient

# public interface
__all__ = ['RefittControllerApp', ]

# application logger
log = Logger.with_name('refittctl')


PROGRAM = 'refittctl'
ACTIONS = ['start', 'stop', 'status', 'restart', 'reload']
ACTION_OPT = '{' + ' | '.join(ACTIONS) + '}'

USAGE = f"""\
usage: {PROGRAM} [-h] [-v] {ACTION_OPT}
{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} <{__contact__}>\
"""

HELP = f"""\
{USAGE}

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

{EPILOG}
"""


def daemon_unavailable(exc: Exception) -> int:  # noqa: exception not used
    """The daemon refused the connection, likely not running."""
    log.critical('Daemon refused connection - is it running?')
    return exit_status.runtime_error


# logging setup for command-line interface
Application.log_critical = log.critical
Application.log_exception = log.critical


class RefittControllerApp(Application):
    """Application class for the refitt daemon controller."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('-v', '--version', version=__version__, action='version')

    action: str = None
    interface.add_argument('action', choices=ACTIONS)

    exceptions = {
        RuntimeError:
            functools.partial(handle_exception, logger=log,
                              status=exit_status.runtime_error),
        ConnectionRefusedError: daemon_unavailable,
        Exception: functools.partial(write_traceback, logger=log),
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
        with DaemonClient() as daemon:
            info = daemon.status

        for service, status in info.items():
            alive = status.pop('alive')
            color = ansi.green if alive else ansi.red
            state = 'alive' if alive else 'dead'
            pid = status.pop('pid')
            print(color(f'● {service}: {state} ({pid})'))
            for key, value in status.items():
                print(f'{key:>10}: {value}')

    def run_action(self) -> None:
        """Run the action."""
        with DaemonClient() as daemon:
            daemon.request(self.action)


def main() -> int:
    """Entry-point for `refittctl` console application."""
    return RefittControllerApp.main(sys.argv[1:])
