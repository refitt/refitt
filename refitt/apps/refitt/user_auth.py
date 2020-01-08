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

"""Manage user credentials for the REFITT database."""

# type annotations
from __future__ import annotations

# standard libs
import os
import functools

# internal libs
from ...database import auth, data, execute
from ...core.exceptions import log_and_exit
from ...core.logging import Logger, SYSLOG_HANDLER
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
NAME = os.path.basename(__file__)[:-3].replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <user_id> [--gen-key] [--gen-token] [--level INT] [--purge]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

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
    --gen-key                Generate a new key.
    --gen-token              Generate a new token.
    --level                  Apply specific authorization level. (default: 2)
    --purge                  Mark all previous credentials as invalid.
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger.with_name(f'{__appname__}.{NAME}')


class UserAuthApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    user_id: str = None
    interface.add_argument('user_id', type=int)

    gen_key: bool = False
    interface.add_argument('--gen-key', action='store_true')

    gen_token: bool = False
    interface.add_argument('--gen-token', action='store_true')

    level: int = 2
    interface.add_argument('--level', type=int, default=level)

    purge: bool = False
    interface.add_argument('--purge', action='store_true')

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
    }

    def run(self) -> None:
        """Run auth management."""

        # check that user_id is valid
        if data['user']['user'].select(where=[f'user_id = {self.user_id}'], limit=1).empty:
            log.error(f'no user account with user_id={self.user_id}')
            return

        # purge all existing credentials if necessary
        if self.purge:
            log.info(f'invalidating all existing credentials for user_id={self.user_id}')
            auth.set_invalid(user_id=self.user_id)

        if not self.gen_token and not self.gen_key:
            return

        # create new credentials
        key = None if not self.gen_key else auth.gen_key()
        new_auth = auth.gen_auth(user_id=self.user_id, key=key, level=self.level)
        auth.put_auth(new_auth)

    def __enter__(self) -> UserAuthApp:
        """Initialize resources."""

        if self.syslog:
            log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        elif self.verbose:
            log.handlers[0].level = log.levels[1]
        else:
            log.handlers[0].level = log.levels[2]

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""


# inherit docstring from module
UserAuthApp.__doc__ = __doc__