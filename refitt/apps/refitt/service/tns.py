# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Query Transient Name Server (tns) for object attributes."""


# type annotations
from __future__ import annotations

# standard libs
import sys
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError
from streamkit.subscriber import Subscriber

# internal libs
from ....data.tns import TNSService

# public interface
__all__ = ['TNSApp', ]


PROGRAM = 'refitt service tns'
USAGE = f"""\
usage: {PROGRAM} [-h] [--from PATH | --live]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --live               Listen for object events.
-f, --from   PATH        File listing object names.
-h, --help               Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class TNSApp(Application):
    """Application class for TNS service."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source_path: str = None
    source_live: bool = False
    source_group = interface.add_mutually_exclusive_group()
    source_group.add_argument('-f', '--from', default=source_path, dest='source_path')
    source_group.add_argument('--live', action='store_true', dest='source_live')

    def run(self) -> None:
        """Run TNS query service."""
        if not self.source_live and not self.source_path:
            raise ArgumentError(f'Must specify either --from=PATH or --live')
        elif self.source_live:
            self.run_live()
        else:
            self.run_from(self.source_path)

    @staticmethod
    def run_live() -> None:
        """Subscribe to broker events and run forever."""
        with Subscriber(name='tns', topics=['refitt.data.broker', ], batchsize=10, poll=4) as subscriber:
            server = TNSService.from_subscriber(subscriber)
            server.run()

    def run_from(self, path: str) -> None:
        """Stream object names from I/O device."""
        if path == '-':
            server = TNSService.from_io(sys.stdin)
            server.run()
        else:
            with open(self.source_path, mode='r') as stream:
                server = TNSService.from_io(stream)
                server.run()
