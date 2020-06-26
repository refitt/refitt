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

"""Dummy service for testing purposes."""

# type annotations
from __future__ import annotations

# standard libs
import time
import random
import functools

# internal libs
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


# program name is constructed from module file name
PROGRAM = f'{__appname__} service test'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} [--name NAME] [--interval SECONDS] [--failure RATE]
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
-n, --name      NAME     Name for logging purposes.
-i, --interval  SECONDS  Time to sleep between heartbeats.
-f, --failure   RATE     Percentage rate [0, 1].
-d, --debug              Show debugging messages.
-v, --verbose            Show information messages.
    --syslog             Use syslog style messages.
-h, --help               Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger(__name__)


class Test(Application):
    """Dummy service for testing purposes."""

    interface = Interface(PROGRAM, USAGE, HELP)

    name: str = 'test'
    interface.add_argument('-n', '--name', default=name)

    interval: float = 1
    interface.add_argument('-i', '--interval', type=float, default=interval)

    failure: float = 0.1
    interface.add_argument('-f', '--failure', type=float, default=failure)

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
        """Simulate failures."""
        while True:
            log.debug(f'[{self.name}] heartbeat')
            time.sleep(self.interval)
            if random.uniform(0, 1) > (1 - self.failure):
                raise RuntimeError(f'[{self.name}] simulated failure occurred!')

    def __enter__(self) -> Test:
        """Initialize resources."""
        cli_setup(self)

        if self.interval < 0:
            raise ArgumentError('--interval must be positive')

        if self.failure < 0 or self.failure > 1:
            raise ArgumentError('--failure must be in the range [0, 1]')

        log.debug(f'starting test service [name={self.name}, interval={self.interval}, '
                  f'failure={self.failure}]')
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
