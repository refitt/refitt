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

"""Set user profile data."""

# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import os
import sys
import json
import functools

# internal libs
from refitt import database
from refitt.database.profile import User, UserNotFound
from refitt.core.exceptions import log_and_exit
from refitt.core.logging import Logger, cli_setup
from refitt.__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# initialize module level logger
log = Logger(__name__)

# program name is constructed from module file name
PROGRAM = f'{__appname__} profile user set'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} FILE [--profile NAME] [-d | -v] [--syslog]
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

arguments:
FILE                     File path to user profile data (JSON).

options:
    --profile   NAME     Name of database profile (e.g., "test").
-d, --debug              Show debugging messages.
-v, --verbose            Show information messages.
    --syslog             Use syslog style messages.
-h, --help               Show this message and exit.

{EPILOG}
"""


class UserSet(Application):
    """Set user profile data."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source: str = '-'
    interface.add_argument('source')

    profile: Optional[str] = None
    interface.add_argument('--profile', default=profile)

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
        UserNotFound: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Set user profiles."""

        if self.source == '-':
            data = sys.stdin.read()
        else:
            with open(self.source, mode='r') as source:
                data = source.read()

        profile = User.from_dict(json.loads(data))
        profile.to_database()

    def __enter__(self) -> UserSet:
        """Initialize resources."""
        cli_setup(self)
        database.connect(profile=self.profile)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
