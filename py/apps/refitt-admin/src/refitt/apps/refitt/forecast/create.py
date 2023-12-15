# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Create new forecast(s)."""


# type annotations
from __future__ import annotations
from typing import IO

# standard libs
import os
import sys
from functools import partial, cached_property

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.core.exceptions import handle_exception
from refitt.core.logging import Logger

# public interface
__all__ = ['ForecastCreateApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt forecast create'
USAGE = f"""\
usage: {PROGRAM} OBJECT [--publish [--print]]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
OBJECT                ID or alias for object.

options:
    --publish         Publish created model(s).
    --print           Print ID of published model. 
-h, --help            Show this message and exit.\
"""


class ForecastCreateApp(Application):
    """Application class for forecast creation."""

    interface = Interface(PROGRAM, USAGE, HELP)

    publish_mode: bool = False
    interface.add_argument('--publish', action='store_true', dest='publish_model')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        IntegrityError: partial(handle_exception, logger=log,
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
