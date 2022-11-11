# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Reduce observation data."""


# type annotations
from __future__ import annotations

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from refitt.core.logging import Logger


# public interface
__all__ = ['ObservationReduceApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt observation reduce'
USAGE = f"""\
usage: {PROGRAM} [-h] FILE
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-h, --help                Show this message and exit.\
"""


class ObservationReduceApp(Application):
    """Application class for reducing observation data."""

    interface = Interface(PROGRAM, USAGE, HELP)

    def run(self) -> None:
        """Business logic of command."""
        log.critical('Not implemented')
