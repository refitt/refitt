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

"""
Exchange Services
=================
"""

# standard libs
from multiprocessing import JoinableQueue
from multiprocessing.managers import SyncManager
from abc import ABC as AbstractBase, abstractstaticmethod
from typing import Tuple, Dict


class Queue(JoinableQueue):
    """A distributed queue accessible over networks."""

    def get(self) -> dict:
        """Retrieve object off queue and signal."""
        obj = super().get()
        self.task_done()
        return obj

    def put(self, data: dict) -> None:
        """Put an object on the queue."""
        super().put(data)


class QueueManager(SyncManager):
    """Exposes access to a shared `Queue` over the network."""

    def __init__(self, address: Tuple[str, int], authkey: bytes) -> None:
        """Initialize manager."""
        super().__init__(address, authkey)
        self.connect()

    def __enter__(self) -> 'QueueManager':
        """Setup context manager."""
        return self

    def __exit__(self, *exc) -> None:
        """Teardown context manager."""
        self.close()


class QueueServer(QueueManager):
    pass


class QueueClient(QueueManager):
    pass


queue = Queue()
QueueServer.register('get_queue', callable=lambda: queue)
QueueClient.register('get_queue')



class MessageServer(AbstractBase):
    """Abstract base class for exchange server node."""

    stream: Queue = None
    admin:  Queue = None

    managers: Dict[str, QueueManager] = None

    def __init__(self) -> None:
        """Initialization."""

    @abstractstaticmethod
    def stream_process(queue: Queue, managers: Dict[str, QueueManager]) -> None:
        """One-to-one or One-to-many implementation."""
        raise NotImplementedError()
