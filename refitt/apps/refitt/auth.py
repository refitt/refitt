# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Generate/update credentials for a user."""


# type annotations
from __future__ import annotations
from typing import Dict, Optional, Union, Callable

# standard libs
import sys
import json
import functools
import logging

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax

# internal libs
from ...database.model import User, Client, Session, NotFound, DEFAULT_EXPIRE_TIME, DEFAULT_CLIENT_LEVEL
from ...core.exceptions import log_exception
from ...web.token import Cipher

# public interface
__all__ = ['AuthApp', ]


PROGRAM = 'refitt auth'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} <user> {{--gen-key [--level NUM] | --gen-secret | --gen-token [--expires SECONDS]}}
       {PROGRAM} [-h] --gen-rootkey
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
user                         ID or alias of user.
action                       See `actions`.

actions:
    --gen-key                Generate all new credentials.
    --gen-secret             Generate new client secret.
    --gen-token              Generate new session token.
    --gen-rootkey            Generate new rootkey.
    --revoke                 Revoke credentials.
    
options:
-e, --expires     SEC        Seconds until token expires (default: {DEFAULT_EXPIRE_TIME}).
-l, --level       NUM        Apply specific authorization level (default: {DEFAULT_CLIENT_LEVEL}).
-h, --help                   Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class AuthApp(Application):
    """Generate new authentication keys/tokens."""

    interface = Interface(PROGRAM, USAGE, HELP)

    user: Union[int, str] = None
    interface.add_argument('user', nargs='?', default=None)

    gen_key: bool = False
    gen_secret: bool = False
    gen_token: bool = False
    revoke_all: bool = False
    gen_rootkey: bool = False
    action_interface = interface.add_mutually_exclusive_group()
    action_interface.add_argument('--gen-key', action='store_true')
    action_interface.add_argument('--gen-secret', action='store_true')
    action_interface.add_argument('--gen-token', action='store_true')
    action_interface.add_argument('--gen-rootkey', action='store_true')
    action_interface.add_argument('--revoke', action='store_true', dest='revoke_all')

    level: Optional[int] = DEFAULT_CLIENT_LEVEL
    interface.add_argument('--level', type=int, default=level)

    expires: float = DEFAULT_EXPIRE_TIME
    interface.add_argument('--expires', type=float, default=DEFAULT_EXPIRE_TIME)

    format_json: bool = False
    interface.add_argument('--json', action='store_true', dest='format_json')

    exceptions = {
        NotFound: functools.partial(log_exception, logger=log.critical, status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Run auth management."""
        self.check_arguments()
        data = self.update_credentials()
        if data:
            self.format_output(data)

    def check_arguments(self) -> None:
        """Additional logical validation of arguments."""
        actions = 'gen_key', 'gen_secret', 'gen_token', 'gen_rootkey', 'revoke_all'
        actions_specified = map(functools.partial(getattr, self), actions)
        if not any(actions_specified):
            raise ArgumentError(f'Must specify action')
        if not self.gen_rootkey and not self.user:
            raise ArgumentError('Must specify <user>')

    def format_output(self, data: Dict[str, str]):
        """Format and print credentials."""
        if self.format_json:
            if sys.stdout.isatty():
                Console().print(Syntax(json.dumps(data, indent=4), 'json', theme='solarized-dark',
                                       word_wrap=True, background_color='default'))
            else:
                print(json.dumps(data, indent=4), file=sys.stdout, flush=True)
        else:
            for field, value in data.items():
                prefix = field + ':'
                print(f'{prefix:<8} {value}', file=sys.stdout, flush=True)

    @property
    def available_actions(self) -> Dict[str, Callable[[], Optional[Dict[str, str]]]]:
        """Mapping of available actions to take."""
        return {
            'gen_key': self.update_key,
            'gen_secret': self.update_secret,
            'gen_token': self.update_token,
            'gen_rootkey': self.create_rootkey,
            'revoke_all': self.revoke_credentials
        }

    @property
    def requested_action(self) -> Callable[[], Optional[Dict[str, str]]]:
        """Determine action to take."""
        for name, action in self.available_actions.items():
            was_requested = getattr(self, name)
            if was_requested:
                return action

    def update_credentials(self) -> Optional[Dict[str, str]]:
        """Apply changes and return credentials if altered."""
        return self.requested_action()

    def revoke_credentials(self) -> None:
        """Set valid=False for client."""
        client_id = Client.from_user(self.user_id).id
        Client.update(client_id, valid=False)

    def update_key(self) -> Dict[str, str]:
        """Generate entirely new set of credentials."""
        try:
            key, secret = Client.new_key(self.user_id)
        except NotFound:
            key, secret, client = Client.new(self.user_id, level=self.level)
        return {'key': key.value, 'secret': secret.value, **self.update_token()}

    def update_secret(self) -> Dict[str, str]:
        """Generate new client secret."""
        key, secret = Client.new_secret(self.user_id)
        return {'key': key.value, 'secret': secret.value, **self.update_token()}

    def update_token(self) -> Dict[str, str]:
        """Only generate a new session token for existing client."""
        token = Session.new(self.user_id, expires=self.expires)
        return {'token': token.encrypt()}

    @staticmethod
    def create_rootkey() -> Dict[str, str]:
        """Generate a new rootkey."""
        return {'rootkey': Cipher.new_rootkey().value, }

    @property
    def user_id(self) -> int:
        """The user's ID (lookup based on `alias` if necessary)."""
        try:
            return int(self.user)
        except ValueError:
            return User.from_alias(self.user).id
