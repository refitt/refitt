# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Request client key/secret for API."""


# standard libs
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from ...web import request
from ...core.config import config

# public interface
__all__ = ['LoginApp', ]


PROGRAM = 'refitt login'
USAGE = f"""\
usage: {PROGRAM} [-h] login [--force]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --force                  Ignore existing key and secret.
-h, --help                   Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class LoginApp(Application):
    """Application class for web login method."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    force: bool = False
    interface.add_argument('--force', action='store_true')

    def run(self) -> None:
        """Run login method."""
        if 'key' in config.api and 'secret' in config.api and not self.force:
            log.info('Already logged in, use --force to get new credentials')
        else:
            request.login(force=self.force)
