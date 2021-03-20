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

"""Publish existing forecast data."""


# type annotations
from __future__ import annotations
from typing import List, IO

# standard libs
import os
import sys
import logging
from functools import partial, cached_property

# internal libs
from ....core.exceptions import log_exception
from ....core.schema import SchemaError
from ....forecast import Forecast

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError

# public interface
__all__ = ['ForecastPublishApp', ]


PROGRAM = 'refitt forecast publish'
USAGE = f"""\
usage: {PROGRAM} FILE [FILE...] [--print]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
FILE                  Path to JSON file(s).

options:
    --print           Print ID of published forecast. 
-h, --help            Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class ForecastPublishApp(Application):
    """Application class for forecast upload."""

    interface = Interface(PROGRAM, USAGE, HELP)

    sources: List[str]
    interface.add_argument('sources', nargs='+')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        ArgumentError: partial(log_exception, logger=log.critical,
                               status=exit_status.bad_argument),
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        IntegrityError: partial(log_exception, logger=log.critical,
                                status=exit_status.runtime_error),
        SchemaError: partial(log_exception, logger=log.critical,
                             status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Business logic of command."""
        self.check_sources()
        for filepath in self.sources:
            self.write(self.load(filepath).publish().id)

    def check_sources(self) -> None:
        """Validate provided file paths."""
        if '-' in self.sources and len(self.sources) > 1:
            raise ArgumentError('Cannot load from <stdin> with multiple sources')
        if '-' not in self.sources:
            for filepath in self.sources:
                if not os.path.exists(filepath):
                    raise RuntimeError(f'File not found: {filepath}')
                if not os.path.isfile(filepath):
                    raise RuntimeError(f'Not a file: {filepath}')

    @staticmethod
    def load(filepath: str) -> Forecast:
        """Load forecast data."""
        if filepath == '-':
            return Forecast.from_io(sys.stdin)
        else:
            return Forecast.from_local(filepath)

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)
