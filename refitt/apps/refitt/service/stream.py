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
from typing import Dict, Type, Callable

# standard libs
import os
import logging
import functools

# internal libs
from ....core.config import config, ConfigurationError
from ....core.exceptions import log_exception
from ....data.broker.alert import AlertInterface
from ....data.broker.client import ClientInterface
from ....data.broker.antares import AntaresClient

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


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


# application logger
log = logging.getLogger('refitt')


# available broker clients
broker_map: Dict[str, Type[ClientInterface]] = {
    'antares': AntaresClient,
}


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

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
        ConfigurationError: functools.partial(log_exception, logger=log.critical,
                                              status=exit_status.bad_config),
    }

    def run(self) -> None:
        """Connect to broker and stream alerts."""
        key = self.get_credential('key')
        secret = self.get_credential('secret')
        client = self.get_client()
        filter_alert = self.get_filter(client)
        log.info(f'Connecting to {self.broker} (topic={self.topic}, filter={self.filter_name})')
        with client(self.topic, (key, secret)) as stream:
            for alert in stream:
                self.process_alert(alert, filter_alert)

    def get_credential(self, name: str) -> str:
        """Fetch from command-line argument or configuration file."""
        cred = getattr(self, name)
        if cred is not None:
            return cred
        try:
            cred = getattr(config['broker'][self.broker], name)  # NOTE: getattr for auto expansion
            log.debug(f'Loaded {self.broker} {name} from configuration')
            return cred
        except (KeyError, AttributeError) as error:
            raise ConfigurationError(f'Option --{name} not given and \'broker.{self.broker}.{name}\' '
                                     'not found in configuration') from error

    def get_client(self) -> Type[ClientInterface]:
        """Check for client interface based on name."""
        try:
            return broker_map[self.broker]
        except KeyError as error:
            raise ArgumentError(f'No broker with name \'{self.broker}\'') from error

    def get_filter(self, client: Type[ClientInterface]) -> Callable[[AlertInterface], bool]:
        """Return bound method of `client` for requested local filter by name."""
        try:
            return getattr(client, f'filter_{self.filter_name}')
        except AttributeError as error:
            raise RuntimeError(f'Local filter \'{self.filter_name}\' not implemented for {self.broker}') from error

    def process_alert(self, alert: AlertInterface, filter_alert: Callable[[AlertInterface], bool]) -> None:
        """Process incoming `alert`, optionally persist to disk and/or database."""
        name = f'{self.broker}::{alert.id})'
        log.info(f'Received ({name})')
        if filter_alert(alert) is False:
            log.info(f'Rejected by filter \'{self.filter_name}\' ({name})')
        else:
            log.info(f'Accepted by filter \'{self.filter_name}\' ({name})')
            self.persist(alert)

    def persist(self, alert: AlertInterface) -> None:
        """Save `alert` to file and/or database."""
        if not self.database_only:
            self.persist_to_disk(alert)
        if not self.local_only:
            self.persist_to_database(alert)

    def persist_to_disk(self, alert: AlertInterface) -> None:
        """Save `alert` to local file."""
        filepath = os.path.join(self.output_directory, f'{alert.id}.json')
        alert.to_local(filepath)
        log.info(f'Written to file ({filepath})')

    def persist_to_database(self, alert: AlertInterface) -> None:
        """Save `alert` to database (backfill if requested)."""
        alert.to_database()
        if self.enable_backfill:
            alert.backfill_database()
