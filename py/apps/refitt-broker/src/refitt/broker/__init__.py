# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Subscribe to remote data brokers/streams."""


# type annotations
from __future__ import annotations
from typing import Tuple, Dict, Type, Callable

# standard libs
import os
import sys

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from refitt.core.config import config, ConfigurationError
from refitt.core.logging import Logger
from refitt.broker.alert import AlertInterface
from refitt.broker.client import ClientInterface
from refitt.broker.antares import AntaresClient

# public interface
__all__ = ['BrokerApp', 'BrokerService', 'broker_map', ]

# module logger
log = Logger.with_name(__name__)


# Available broker clients
broker_map: Dict[str, Type[ClientInterface]] = {
    'antares': AntaresClient,
}


class BrokerService:
    """Subscribe to remote data brokers and stream alerts."""

    broker: str
    topic: str
    key: str
    secret: str
    filter_name: str
    output_dir: str
    local_only: bool
    database_only: bool
    enable_backfill: bool

    def __init__(self, broker: str, topic: str, credentials: Tuple[str, str],
                 filter_name: str = 'none', output_dir: str = os.getcwd(),
                 local_only: bool = False, database_only: bool = False,
                 enable_backfill: bool = False) -> None:
        """Initialize parameters."""
        self.broker = broker
        self.topic = topic
        self.key, self.secret = credentials
        self.filter_name = filter_name
        self.output_dir = output_dir
        self.local_only = local_only
        self.database_only = database_only
        self.enable_backfill = enable_backfill

    def run(self) -> None:
        """Connect to broker and stream alerts."""
        key = self.get_credential('key')
        secret = self.get_credential('secret')
        client_interface = self.get_client()
        alert_filter = self.get_filter(client_interface)
        log.info(f'Connecting to {self.broker} (topic={self.topic}, filter={self.filter_name})')
        with client_interface(self.topic, (key, secret)) as stream:
            for alert_instance in stream:
                self.process_alert(alert_instance, alert_filter)

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
            raise NameError(f'No broker with name \'{self.broker}\'') from error

    def get_filter(self, client_interface: Type[ClientInterface]) -> Callable[[AlertInterface], bool]:
        """Return bound method of `client_interface` for requested local filter by name."""
        try:
            return getattr(client_interface, f'filter_{self.filter_name}')
        except AttributeError as error:
            raise AttributeError(f'Local filter \'{self.filter_name}\' not implemented for {self.broker}') from error

    def process_alert(self, alert_instance: AlertInterface, filter_alert: Callable[[AlertInterface], bool]) -> None:
        """Process incoming `alert_instance`, optionally persist to disk and/or database."""
        name = f'{self.broker}::{alert_instance.id}'
        log.info(f'Received {name}')
        if filter_alert(alert_instance) is False:
            log.info(f'Rejected by filter \'{self.filter_name}\' ({name})')
        else:
            log.info(f'Accepted by filter \'{self.filter_name}\' ({name})')
            if not self.database_only:
                self.persist_to_disk(alert_instance)
            if not self.local_only:
                self.persist_to_database(alert_instance, name)

    def persist_to_disk(self, alert_instance: AlertInterface) -> None:
        """Save `alert` to local file."""
        filepath = os.path.join(self.output_dir, f'{alert_instance.id}.json')
        alert_instance.to_local(filepath)
        log.info(f'Written to file ({filepath})')

    def persist_to_database(self, alert_instance: AlertInterface, name: str) -> None:
        """Save `alert` to database (backfill if requested)."""
        alert_instance.to_database()
        log.info(f'Written to database ({name})')
        if self.enable_backfill:
            log.debug(f'Backfilling observations ({name})')
            alert_instance.backfill_database()


PROGRAM = f'refitt-broker'
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


class BrokerApp(Application):
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


def main() -> int:
    """Entry-point for `refitt-broker` console application."""
    return BrokerApp.main(sys.argv[1:])
