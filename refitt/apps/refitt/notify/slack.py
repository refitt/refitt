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
import functools

# internal libs
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
PROGRAM = f'{__appname__} notify slack'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} CHANNEL [MESSAGE] [--from BOT]
       {PADDING} [--attach FILE]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

{__doc__}
If no message/file is given it will be read from standard input.\
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
CHANNEL                  Name of the channel.
MESSAGE                  A message or @FILE.

options:
-f, --from      NAME     Name of bot account to use.
-a, --attach    FILE     Path to file for attachment.
-d, --debug              Show debugging messages.
-v, --verbose            Show information messages.
    --syslog             Use syslog style messages.
-h, --help               Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger(__name__)


class Slack(Application):
    """Post slack messages and files."""

    interface = Interface(PROGRAM, USAGE, HELP)

    channel: str = None
    interface.add_argument('channel')

    message: str = '@-'
    interface.add_argument('message', default=message)

    botname: str = 'refitt'
    interface.add_argument('-f', '--from', default=botname, dest='botname')

    attachment: List[str] = None
    interface.add_argument('-a', '--attach', dest='attachment')

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
        """Create and send email."""
        raise RuntimeError('slack integration is not implemented')

    def __enter__(self) -> Slack:
        """Initialize resources."""
        cli_setup(self)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
