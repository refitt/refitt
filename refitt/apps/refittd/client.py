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

"""Refitt daemon service manager client implementation."""

# type annotations
from __future__ import annotations

# standard libs
from multiprocessing import JoinableQueue, TimeoutError
from multiprocessing.managers import BaseManager

# internal libs
from ...core.config import VARS
from ...core.logging import Logger


# initialize module level logger
log = Logger(__name__)


class RefittDaemonClient(BaseManager):
    """Connect to the RefittDaemonServer."""

    _queue: JoinableQueue = None
    _status: JoinableQueue = None

    def __init__(self) -> None:
        """Initialize the queue."""
        super().__init__(address=('localhost', int(VARS['DAEMON_PORT'])),
                         authkey=VARS['DAEMON_KEY'].encode())
        self.register('_get_queue')
        self.register('_get_status')

    def request(self, action: str) -> None:
        """Put an `action` on the shared queue."""
        try:
            self._queue.put(action, timeout=10)
        except TimeoutError:
            log.error(f'timeout reached on action "{action}"')

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

    def __enter__(self) -> RefittDaemonClient:
        """Connect to the server."""
        self.connect()
        self._queue = self._get_queue()  # pylint: disable=no-member
        self._status = self._get_status()  # pylint: disable=no-member
        log.debug('connected to refittd server')
        return self

    def __exit__(self, *exc) -> None:
        """Disconnect from the server."""
        log.debug('disconnected from refittd server')
