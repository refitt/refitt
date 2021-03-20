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

"""Create new forecast."""


# type annotations
from __future__ import annotations
from typing import IO

# standard libs
import os
import sys
import logging
from functools import partial, cached_property

# internal libs
from ....core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError


PROGRAM = 'refitt forecast create'
USAGE = f"""\
usage: {PROGRAM} OBJECT [--publish [--print]]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
OBJECT                ID or alias for object to forecast.

options:
    --publish         Upload created forecast.
    --print           Print ID of published forecast. 
-h, --help            Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class ForecastCreateApp(Application):
    """Application class for forecast creation."""

    interface = Interface(PROGRAM, USAGE, HELP)

    publish_mode: bool = False
    interface.add_argument('--publish', action='store_true', dest='publish_model')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        ArgumentError: partial(log_exception, logger=log.critical,
                               status=exit_status.bad_argument),
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        IntegrityError: partial(log_exception, logger=log.critical,
                                status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Business logic of command."""
        raise RuntimeError('Not implemented')

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)
