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

"""Get user profile data."""

# type annotations
from __future__ import annotations
from typing import Optional, Iterable, Mapping

# standard libs
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
PROGRAM = f'{__appname__} profile user get'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{ID | ALIAS}} [-x VAR] [-1] [--profile NAME] [-d | -v] [--syslog]
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
ID                       ID of user.
ALIAS                    Alias of user.

options:
-1, --oneline            Put output on one line.
-x, --extract   VAR      Extract the given variable.
    --profile   NAME     Name of database profile (e.g., "test").
-d, --debug              Show debugging messages.
-v, --verbose            Show information messages.
    --syslog             Use syslog style messages.
-h, --help               Show this message and exit.

{EPILOG}
"""


class UserGet(Application):
    """Get user profile data."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source: str = None
    interface.add_argument('source')

    attribute: str = None
    interface.add_argument('-x', dest='attribute', default=None)

    oneline: bool = False
    interface.add_argument('-1', '--oneline', action='store_true')

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
        """Get user profile."""

        try:
            profile = User.from_id(int(self.source))
        except (ValueError, TypeError):
            profile = User.from_alias(self.source)

        data = profile.to_dict()
        if self.attribute is not None:
            if self.attribute not in data:
                raise RuntimeError(f'"{self.attribute}" not an attribute of user '
                                   f'"{self.source}"')
            value = data[self.attribute]
            if not isinstance(value, str) and isinstance(value, (Mapping, Iterable)):
                indent = 4 if self.oneline is False else None
                print(json.dumps(value, indent=indent))
            else:
                print(value)
        else:
            indent = 4 if self.oneline is False else None
            print(json.dumps(data, indent=indent))

    def __enter__(self) -> UserGet:
        """Initialize resources."""
        cli_setup(self)
        database.connect(profile=self.profile)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
