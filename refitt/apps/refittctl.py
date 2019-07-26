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

"""The refitt controller."""

# internal libs
from ..core.logging import logger
from ..__meta__ import (__appname__, __version__, __copyright__,
                        __developer__, __contact__, __website__)

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError, HelpOption


PROGRAM = f'{__appname__}ctl'
USAGE = f"""\
usage: {PROGRAM} {{start | stop | status}}
       {PROGRAM} [--help] [--version]

{__doc__}
This program should not be called directly.\
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
log = logger.with_name(PROGRAM)


ACTIONS = {
    'start': None,
    'stop': None,
    'status': None
}

class RefittController(Application):
    """Application class for the refitt service daemon, `refittd`."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('--version', version=__version__, action='version')

    action: str = None
    interface.add_argument('action', choices=list(ACTIONS))

    def run(self) -> None:
        """Start the refitt service daemon."""
        if self.action == 'status':
            log.info('checking status of refitt ...')
        else:
            log.info(f'{self.action}ing refitt ...')


def main() -> int:
    """Entry-point for `refittd` console application."""
    return RefittController.main()
