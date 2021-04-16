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

"""Subscribe to remote data brokers/streams."""


# type annotations
from typing import Tuple, Dict, Type, Callable

# standard libs
import os
import logging

# internal libs
from ...core.config import config, ConfigurationError
from .alert import AlertInterface
from .client import ClientInterface
from .antares import AntaresClient


# initialize module level logger
log = logging.getLogger(__name__)


# available broker clients
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
            for __alert in stream:
                self.process_alert(__alert, alert_filter)

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

    def get_filter(self, __client: Type[ClientInterface]) -> Callable[[AlertInterface], bool]:
        """Return bound method of `__client` for requested local filter by name."""
        try:
            return getattr(__client, f'filter_{self.filter_name}')
        except AttributeError as error:
            raise AttributeError(f'Local filter \'{self.filter_name}\' not implemented for {self.broker}') from error

    def process_alert(self, __alert: AlertInterface, filter_alert: Callable[[AlertInterface], bool]) -> None:
        """Process incoming `alert`, optionally persist to disk and/or database."""
        name = f'{self.broker}::{__alert.id}'
        log.info(f'Received {name}')
        if filter_alert(__alert) is False:
            log.info(f'Rejected by filter \'{self.filter_name}\' ({name})')
        else:
            log.info(f'Accepted by filter \'{self.filter_name}\' ({name})')
            self.persist(__alert)

    def persist(self, __alert: AlertInterface) -> None:
        """Save `alert` to file and/or database."""
        if not self.database_only:
            self.persist_to_disk(__alert)
        if not self.local_only:
            self.persist_to_database(__alert)

    def persist_to_disk(self, __alert: AlertInterface) -> None:
        """Save `alert` to local file."""
        filepath = os.path.join(self.output_dir, f'{__alert.id}.json')
        __alert.to_local(filepath)
        log.info(f'Written to file ({filepath})')

    def persist_to_database(self, __alert: AlertInterface) -> None:
        """Save `alert` to database (backfill if requested)."""
        __alert.to_database()
        if self.enable_backfill:
            __alert.backfill_database()
