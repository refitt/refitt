# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Query Transient Name Server (tns) for object attributes."""


# type annotations
from __future__ import annotations
from typing import IO, Iterator

# standard libs
import sys
import time
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
usage: {PROGRAM} [-h] [[--persist] --from PATH | --live] [--workers NUM]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --live               Listen for object events.
-f, --from     PATH      File listing object names.
-w, --workers  NUM       Number of threads used.
-h, --help               Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


# Time to wait before reading a line from a file if persisting
FILE_SLEEP_PERIOD: int = 4  # seconds


class TNSApp(Application):
    """Application class for TNS service."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source_path: str = None
    source_live: bool = False
    source_group = interface.add_mutually_exclusive_group()
    source_group.add_argument('-f', '--from', default=source_path, dest='source_path')
    source_group.add_argument('--live', action='store_true', dest='source_live')

    source_persist: bool = False
    interface.add_argument('-p', '--persist', action='store_true', dest='source_persist')

    num_workers: int = 1
    interface.add_argument('-w', '--workers', type=int, default=num_workers, dest='num_workers')

    def run(self) -> None:
        """Run TNS query service."""
        if not self.source_live and not self.source_path:
            raise ArgumentError(f'Must specify either --from=PATH or --live')
        elif self.source_live:
            self.run_live()
        else:
            self.run_from(self.source_path)

    def run_live(self) -> None:
        """Subscribe to broker events and run forever."""
        with Subscriber(name='tns', topics=['refitt.data.broker', ], batchsize=10, poll=4) as subscriber:
            server = TNSService.from_subscriber(subscriber, threads=self.num_workers)
            server.run()

    def run_from(self, path: str) -> None:
        """Stream object names from I/O device."""
        if path == '-':
            server = TNSService.from_io(sys.stdin, threads=self.num_workers)
            server.run()
        else:
            with open(self.source_path, mode='r') as stream:
                if not self.source_persist:
                    server = TNSService.from_io(stream, threads=self.num_workers)
                    server.run()
                else:
                    server = TNSService(source=self.yield_forever(stream), threads=self.num_workers)
                    server.run()

    def yield_forever(self, stream: IO) -> Iterator[str]:
        """Yield lines from `stream`, keep waiting until new data arrives."""
        while True:
            if name := stream.readline().strip():
                yield name
            else:
                log.debug(f'Waiting on data ({self.source_path})')
                time.sleep(FILE_SLEEP_PERIOD)
