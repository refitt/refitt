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

"""Post slack messages and files."""


# type annotations
from __future__ import annotations
from typing import List

# standard libs
import logging
import functools

# internal libs
from ....core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


PROGRAM = f'refitt notify slack'
USAGE = f"""\
usage: {PROGRAM} [-h] CHANNEL [MESSAGE] [--from BOT] [--attach FILE]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
CHANNEL                  Name of the channel.
MESSAGE                  A message or @FILE.

options:
-f, --from      NAME     Name of bot account to use.
-a, --attach    FILE     Path to file for attachment.
-h, --help               Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class SlackApp(Application):
    """Application class for slack notifications."""

    interface = Interface(PROGRAM, USAGE, HELP)

    channel: str = None
    interface.add_argument('channel')

    message: str = '@-'
    interface.add_argument('message', default=message)

    botname: str = 'refitt'
    interface.add_argument('-f', '--from', default=botname, dest='botname')

    attachment: List[str] = None
    interface.add_argument('-a', '--attach', dest='attachment')

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Business logic for application class."""
        raise RuntimeError('Slack integration is not implemented')
