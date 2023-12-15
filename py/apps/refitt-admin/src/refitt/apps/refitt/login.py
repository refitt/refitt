# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Request client key/secret for API."""


# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from refitt.core.config import config
from refitt.core.logging import Logger
from refitt.web import request

# public interface
__all__ = ['LoginApp', ]

# application logger
log = Logger.with_name('refitt')


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


class LoginApp(Application):
    """Application class for web login method."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    force: bool = False
    interface.add_argument('--force', action='store_true')

    def run(self) -> None:
        """Run login method."""
        if self.force:
            request.login(force=True)
            return
        try:
            getattr(config.api, 'key')
            getattr(config.api, 'secret')
        except AttributeError:
            request.login()
        else:
            log.info('Already logged in, use --force to get new credentials')
