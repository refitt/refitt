# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Refitt daemon service manager client implementation."""


# type annotations
from __future__ import annotations
from typing import Optional, Callable

# standard libs
import logging
from multiprocessing import JoinableQueue, TimeoutError
from multiprocessing.managers import BaseManager

# internal libs
from ..core.config import config

# public interface
__all__ = ['DaemonClient', ]


# initialize module level logger
log = logging.getLogger(__name__)


class DaemonClient(BaseManager):
    """Connect to the RefittDaemonServer."""

    _queue: JoinableQueue = None
    _status: JoinableQueue = None

    _get_queue: Optional[Callable[[], JoinableQueue]] = None
    _get_status: Optional[Callable[[], JoinableQueue]] = None

    def __init__(self) -> None:
        """Initialize the queue."""
        super().__init__(address=('localhost', int(config.daemon.port)), authkey=config.daemon.key.encode())
        self.register('_get_queue')
        self.register('_get_status')

    def request(self, action: str) -> None:
        """Put an `action` on the shared queue."""
        try:
            self._queue.put(action, timeout=10)
        except TimeoutError:
            log.error(f'Timeout reached on action \'{action}\'')

    @property
    def status(self) -> dict:
        """Request the status of running services."""
        # NOTE: the first "flush" makes us wait until the "status"
        #       has been pulled off the queue. The second "flush"
        #       ensures that the "status" was finished.
        self.request('status')
        self.request('flush')
        self.request('flush')
        return self._poll_status()

    def _poll_status(self) -> dict:
        """Last known status of running services."""
        value = self._status.get()
        self._status.put(value)
        self._status.task_done()
        return value

    def __enter__(self) -> DaemonClient:
        """Connect to the server."""
        self.connect()
        self._queue = self._get_queue()
        self._status = self._get_status()
        log.debug('Connected to daemon manager')
        return self

    def __exit__(self, *exc) -> None:
        """Disconnect from the server."""
        log.debug('Disconnected from daemon manager')
