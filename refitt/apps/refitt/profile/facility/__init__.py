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

"""Manage facility profiles."""

# standard libs
import sys

# internal libs
from .....core.exceptions import CompletedCommand
from .....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# commands
from .get import FacilityGet
from .set import FacilitySet


COMMANDS = {
    'get': FacilityGet,
    'set': FacilitySet,
}

PROGRAM = f'{__appname__} profile facility'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} [--help] <action> [<args>...] [--help]
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

actions:
get                  {FacilityGet.__doc__}
set                  {FacilitySet.__doc__}

options:
-h, --help           Show this message and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.

{EPILOG}\
"""


class FacilityGroup(Application):
    """Manage facility profiles."""

    interface = Interface(PROGRAM, USAGE, HELP)

    command: str = None
    interface.add_argument('command')

    exceptions = {
        CompletedCommand: (lambda exc: int(exc.args[0])),
    }

    def run(self) -> None:
        """Show usage/help/version or defer to command."""

        if self.command in COMMANDS:
            status = COMMANDS[self.command].main(sys.argv[4:])
            raise CompletedCommand(status)
        else:
            raise ArgumentError(f'"{self.command}" is not a command.')
