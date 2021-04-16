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

"""Subscribe to remote data broker."""


# type annotations
from __future__ import annotations

# standard libs
import os

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from ....data.broker import BrokerService

# public interface
__all__ = ['StreamApp', ]


PROGRAM = f'refitt service stream'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <broker> <topic> [--filter NAME] [--backfill] ...
       {PADDING} [--local-only [--output-directory DIR] | --database-only]

{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
<broker>                       Name of broker (e.g., "antares").
<topic>                        Name of topic (e.g., "extragalactic").

options:
--key                   STR    API key for broker.
--secret                STR    API secret for broker.
-o, --output-directory  DIR    Path to directory for alert files (default $CWD).
    --local-only               Do not write alerts to the database.
    --database-only            Do not write alerts to local files.
    --backfill                 Enable backfill for alert stream.
-f, --filter            NAME   Name of filter to reject alerts.
-h, --help                     Show this message and exit.\
"""


class StreamApp(Application):
    """Subscribe to remote data brokers and stream alerts."""

    interface = Interface(PROGRAM, USAGE, HELP)

    broker: str = None
    interface.add_argument('broker')

    topic: str = None
    interface.add_argument('topic')

    key: str = None
    interface.add_argument('--key', default=key)

    secret: str = None
    interface.add_argument('--secret', default=secret)

    filter_name: str = 'none'
    interface.add_argument('--filter', dest='filter_name', default=filter_name)

    output_directory: str = os.getcwd()
    interface.add_argument('-o', '--output-directory', default=output_directory)

    local_only: bool = False
    database_only: bool = False
    output_interface = interface.add_mutually_exclusive_group()
    output_interface.add_argument('--local-only', action='store_true')
    output_interface.add_argument('--database-only', action='store_true')

    enable_backfill: bool = False
    interface.add_argument('--backfill', action='store_true', dest='enable_backfill')

    def run(self) -> None:
        """Connect to broker and stream alerts."""
        service = BrokerService(self.broker, self.topic, (self.key, self.secret),
                                self.filter_name, self.output_directory, self.local_only,
                                self.database_only, self.enable_backfill)
        service.run()
