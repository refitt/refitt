# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) query interface, manager, and services."""


# type annotations
from __future__ import annotations

import re
from queue import Queue
from typing import Iterable, IO, Iterator

# standard libs
import logging

# external libs
from streamkit.subscriber import Subscriber

# internal libs
from .interface import TNSInterface, TNSError, TNSConfig, TNSNameSearchResult, TNSObjectSearchResult
from .manager import TNSManager

# public interface
__all__ = ['TNSInterface', 'TNSError', 'TNSConfig', 'TNSNameSearchResult', 'TNSObjectSearchResult',
           'TNSManager', 'TNSService', ]


# initialize module level logger
log = logging.getLogger(__name__)


# message pattern for alert ingest from brokers
MESSAGE_PATTERN = re.compile(r"Written to database \(([a-z]+)::([a-zA-Z0-9]+)\)")


class TNSService:
    """Object info update service using TNS query interface."""

    source: Iterable[str]
    manager: TNSManager

    def __init__(self, source: Iterable[str], manager: TNSManager = None) -> None:
        """Directly initialize TNS service with a `source` of names."""
        self.source = source
        self.manager = manager or TNSManager.from_config()

    def run(self) -> None:
        """Run service until `source` exhausted (if ever)."""
        for name in self.source:
            self.update_object(name)

    def update_object(self, name: str) -> None:
        """Attempt to update information on object (`name`) in database."""
        try:
            self.manager.update_object(name)
        except TNSError as error:
            log.error(str(error))

    @classmethod
    def from_io(cls, stream: IO) -> TNSService:
        """Initialize TNSService from iterable I/O `stream`."""
        return cls(cls.__yield_names_from_io(stream))

    @classmethod
    def from_queue(cls, queue: Queue) -> TNSService:
        """Initialize TNService from iterable `queue`."""
        return cls(iter(queue.get, None))

    @classmethod
    def from_subscriber(cls, subscriber: Subscriber) -> TNSService:
        """Initialize TNSService with subscriber stream."""
        return cls(cls.__yield_names_from_subscriber(subscriber))

    @staticmethod
    def __yield_names_from_subscriber(subscriber: Subscriber) -> Iterator[str]:
        """Parse object name from broker alert ingest events."""
        for message in subscriber:
            if match := MESSAGE_PATTERN.match(message.text):
                provider, name = match.groups()
                yield name

    @staticmethod
    def __yield_names_from_io(stream: IO) -> Iterator[str]:
        """Pull names from `stream` and strip whitespace."""
        yield from map(lambda name: name.strip(), stream)
