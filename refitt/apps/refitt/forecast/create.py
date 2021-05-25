# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Create new forecast."""


# type annotations
from __future__ import annotations
from typing import IO

# standard libs
import os
import sys
import logging
from functools import partial, cached_property

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError

# internal libs
from ....core.exceptions import log_exception

# public interface
__all__ = ['ForecastCreateApp', ]


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
