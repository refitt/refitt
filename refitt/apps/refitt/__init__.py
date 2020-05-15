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

"""Entry-point for refitt command line interface."""

# standard libs
import sys

# internal libs
from ...core.logging import Logger
from ...core.exceptions import CompletedCommand
from ...__meta__ import (__appname__, __version__, __description__,
                         __copyright__, __developer__, __contact__,
                         __website__, __ascii_art__)

# external libs
from cmdkit import logging as _cmdkit_logging
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# command groups
from .pipeline import PipelineGroup
from .service import ServiceGroup
from .database import DatabaseGroup
from .profile import ProfileGroup
from .notify import NotifyGroup
from .config import ConfigGroup
from .auth import AuthGroup


GROUPS = {
    'pipeline': PipelineGroup,
    'database': DatabaseGroup,
    'service':  ServiceGroup,
    'profile':  ProfileGroup,
    'notify':   NotifyGroup,
    'config':   ConfigGroup,
    'auth':     AuthGroup,
}

PROGRAM = __appname__

USAGE = f"""\
usage: {PROGRAM} <group> <command>... [<args>...]
       {PROGRAM} [--help] [--version]

{__description__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

groups:
pipeline               {PipelineGroup.__doc__}
database               {DatabaseGroup.__doc__}
service                {ServiceGroup.__doc__}
profile                {ProfileGroup.__doc__}
notify                 {NotifyGroup.__doc__}
config                 {ConfigGroup.__doc__}
auth                   {AuthGroup.__doc__}

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.

{EPILOG}\
"""


# initialize module level logger
log = Logger(__name__)


# inject logger back into cmdkit library
_cmdkit_logging.log = log
Application.log_error = log.critical


class Refitt(Application):
    """Application class for primary Refitt console-app."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('-v', '--version', version=__version__, action='version')
    interface.add_argument('--ascii-art', version=__ascii_art__, action='version')

    group: str = None
    interface.add_argument('group')

    exceptions = {
        CompletedCommand: (lambda exc: int(exc.args[0])),
    }

    def run(self) -> None:
        """Show usage/help/version or defer to group."""

        if self.group in GROUPS:
            status = GROUPS[self.group].main(sys.argv[2:3])  # only the sub-command if present
            raise CompletedCommand(status)
        else:
            raise ArgumentError(f'"{self.group}" is not a command group.')


def main() -> int:
    """Entry-point for refitt command line interface."""
    return Refitt.main(sys.argv[1:2])  # only the group if present
