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

"""Generate new authentication keys/tokens."""

# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import sys
import json
import functools
from datetime import timedelta

# internal libs
from .... import database
from ....database.auth import Client, Access, ClientNotFound, DEFAULT_CLIENT_LEVEL, DEFAULT_EXPIRE_TIME
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
PROGRAM = f'{__appname__} auth create'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <user_id> [--gen-key] [--gen-secret] [--gen-token] 
       {PADDING} [--level INT] [--expires HOURS] [--profile NAME]
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
    --gen-key                Revoke previous credentials.
    --gen-secret             Generate new client secret.
    --gen-token              Generate new access token.
    --expires     HOURS      Decimal hours until token expires (default: {DEFAULT_EXPIRE_TIME}).
    --level       INT        Apply specific authorization level (default: {DEFAULT_CLIENT_LEVEL}).
    --profile     NAME       Name of database profile (e.g., "test").
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger(__name__)


class Create(Application):
    """Generate new authentication keys/tokens."""

    interface = Interface(PROGRAM, USAGE, HELP)

    user_id: int = None
    interface.add_argument('user_id', type=int)

    gen_key: bool = False
    interface.add_argument('--gen-key', action='store_true')

    gen_secret: bool = False
    interface.add_argument('--gen-secret', action='store_true')

    gen_token: bool = False
    interface.add_argument('--gen-token', action='store_true')

    level: Optional[int] = DEFAULT_CLIENT_LEVEL
    interface.add_argument('--level', type=int, default=level)

    expires: float = DEFAULT_EXPIRE_TIME
    interface.add_argument('--expires', type=float, default=DEFAULT_EXPIRE_TIME)

    format_json: bool = False
    interface.add_argument('--json', action='store_true', dest='format_json')

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
    }

    def run(self) -> None:
        """Run auth management."""
        if not self.gen_key and not self.gen_secret:
            self.run_token()
        else:
            self.run_full()

    def run_token(self) -> None:
        """Only generate a new access token for existing client."""
        try:
            exptime = None if self.expires == -1 else timedelta(hours=self.expires)
            client = Client.from_user(self.user_id)
            token = Access.new_token(client.client_id, exptime)
            data = token.embed()
        except ClientNotFound as error:
            raise RuntimeError(f'no existing client for user_id={self.user_id}') from error
        if self.format_json:
            print(json.dumps(data, indent=4), file=sys.stdout, flush=True)
        else:
            print(data['access_token'], file=sys.stdout, flush=True)

    def run_full(self) -> None:
        # clearing old credentials triggers new key generation
        if self.gen_key:
            try:
                client = Client.from_user(self.user_id)
                client.remove(client.client_id)
            except ClientNotFound:
                pass

        # create new credentials
        client = Client.new(self.user_id, self.level)
        output = client.embed()

        if self.gen_token:
            token = Access.new_token(client.client_id, timedelta(hours=self.expires))
            output = {**output, **token.embed()}

        if self.format_json:
            print(json.dumps(output, indent=4), file=sys.stdout, flush=True)
        else:
            print(f'client_key:    {output["client_key"]}',    flush=True)
            print(f'client_secret: {output["client_secret"]}', flush=True)
            if self.gen_token:
                print(f'access_token:  {output["access_token"]}', flush=True)

    def __enter__(self) -> Create:
        """Initialize resources."""
        cli_setup(self)
        database.connect(profile=self.profile)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
