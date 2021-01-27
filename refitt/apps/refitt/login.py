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

"""Request client key/secret for API."""


# standard libs
import functools
import logging

# internal libs
from ...web import request
from ...core.config import config
from ...core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


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

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Run login method."""
        if 'key' in config.api and 'secret' in config.api and not self.force:
            log.info('Already logged in, use --force to get new credentials')
        else:
            request.login(force=self.force)
