# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""TNS workers, threads, and master service."""


# type annotations
from __future__ import annotations
from typing import List, IO, Iterable, Iterator

# standard libs
import re
import logging
from threading import Thread
from queue import Queue

# external libs
from streamkit.subscriber import Subscriber

# internal libs
from .interface import TNSError
from .manager import TNSManager

# public interface
__all__ = ['TNSServiceWorker', 'TNSServiceThread', 'TNSService', ]


# initialize module level logger
log = logging.getLogger(__name__)


# message pattern for alert ingest from brokers
MESSAGE_PATTERN = re.compile(r"Written to database \(([a-z]+)::([a-zA-Z0-9]+)\)")


# sentinel value signalling stop iteration on queue-based service workers
STOP_ITER = ''


class TNSServiceWorker:
    """Object info update service worker using TNS query interface."""

    source: Iterable[str]
    manager: TNSManager

    def __init__(self, source: Iterable[str]) -> None:
        """Directly initialize TNS service worker with a `source` of names."""
        self.source = source
        self.manager = TNSManager.from_config()

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
    def from_queue(cls, queue: Queue) -> TNSServiceWorker:
        """Initialize from iterable `queue`."""
        return cls(iter(queue.get, STOP_ITER))


class TNSServiceThread(Thread):
    """Embed `TSNServiceWorker` within isolated thread."""

    service: TNSServiceWorker

    def __init__(self, thread_id: int, queue: Queue) -> None:
        """Initialize thread with integer identifier and queue for names."""
        self.service = TNSServiceWorker.from_queue(queue)
        super().__init__(name=f'TNSServerThread-{thread_id}')

    def run(self) -> None:
        """Run the service worker."""
        log.debug(f'Starting {self.name}')
        self.service.run()


# we only assume one worker thread by default
DEFAULT_THREAD_COUNT: int = 1


class TNSService:
    """Launch and feed one or more service workers."""

    queue: Queue[str]
    source: Iterable[str]
    workers: List[TNSServiceThread]

    def __init__(self, source: Iterable[str], threads: int = DEFAULT_THREAD_COUNT) -> None:
        """Initialize service from iterable `source` of names."""
        self.source = source
        self.queue = Queue(maxsize=threads)
        self.workers = [TNSServiceThread(num + 1, self.queue) for num in range(threads)]

    def run(self) -> None:
        """Start worker threads and feed queue names."""
        for worker in self.workers:
            worker.start()
        for name in self.source:
            self.queue.put(name)
        for _ in self.workers:
            self.queue.put(STOP_ITER)
        for worker in self.workers:
            worker.join()

    @classmethod
    def from_io(cls, stream: IO, threads: int = DEFAULT_THREAD_COUNT) -> TNSService:
        """Initialize TNSServiceWorker from iterable I/O `stream`."""
        return cls(cls.__yield_names_from_io(stream), threads=threads)

    @classmethod
    def from_subscriber(cls, subscriber: Subscriber, threads: int = DEFAULT_THREAD_COUNT) -> TNSService:
        """Initialize TNSServiceWorker with subscriber stream."""
        return cls(cls.__yield_names_from_subscriber(subscriber), threads=threads)

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
