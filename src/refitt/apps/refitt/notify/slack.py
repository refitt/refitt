# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Post slack messages and files."""


# type annotations
from __future__ import annotations
from typing import List

# standard libs
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# public interface
__all__ = ['SlackApp', ]


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

    def run(self) -> None:
        """Business logic for application class."""
        raise RuntimeError('Slack integration is not implemented')
