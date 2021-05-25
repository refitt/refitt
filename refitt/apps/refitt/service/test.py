# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Dummy service for testing purposes."""


# type annotations
from __future__ import annotations

# standard libs
import time
import random
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# public interface
__all__ = ['TestApp', ]


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
