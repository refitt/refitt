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
import logging
import functools

# internal libs
from ....core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = 'refitt service test'
USAGE = f"""\
usage: {PROGRAM} [-h] [--name NAME] [--interval SECONDS] [--failure RATE]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-n, --name      NAME     Name for logging purposes.
-i, --interval  SECONDS  Time to sleep between heartbeats.
-f, --failure   RATE     Percentage rate [0, 1].
-h, --help               Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class TestApp(Application):
    """Application class for test service."""

    interface = Interface(PROGRAM, USAGE, HELP)

    name: str = 'test'
    interface.add_argument('-n', '--name', default=name)

    interval: float = 1
    interface.add_argument('-i', '--interval', type=float, default=interval)

    failure: float = 0.1
    interface.add_argument('-f', '--failure', type=float, default=failure)

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Simulate failures."""
        if self.interval < 0:
            raise ArgumentError('--interval must be positive')
        if self.failure < 0 or self.failure > 1:
            raise ArgumentError('--failure must be in the range [0, 1]')
        log.debug(f'Starting test service [name={self.name}, interval={self.interval}, '
                  f'failure={self.failure}]')
        while True:
            log.debug(f'[{self.name}] heartbeat')
            time.sleep(self.interval)
            if random.uniform(0, 1) > (1 - self.failure):
                raise RuntimeError(f'[{self.name}] Simulated failure occurred')
