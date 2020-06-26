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

"""Refitt daemon service manager implementation."""

# type annotations
from __future__ import annotations

# standard libs
from multiprocessing import JoinableQueue
from multiprocessing.managers import BaseManager

# internal libs
from ...core.config import VARS
from ...core.logging import Logger


# initialize module level logger
log = Logger(__name__)


DAEMON_REFRESH_TIME = float(VARS['DAEMON_REFRESH_TIME'])
class RefittDaemonServer(BaseManager):
    """Serve managed queue of actions."""

    _queue: JoinableQueue = None
    _status: JoinableQueue = None

    def __init__(self) -> None:
        """Initialize the queue."""
        super().__init__(address=('localhost', int(VARS['DAEMON_PORT'])),
                         authkey=VARS['DAEMON_KEY'].encode())
        self._queue = JoinableQueue(maxsize=1)  # single action at a time
        self._status = JoinableQueue(maxsize=1)  # holds current status of services
        self._status.put({})  # no services to start with
        self.register('_get_queue', callable=self._get_queue)
        self.register('_get_status', callable=self._get_status)

    def _get_queue(self) -> JoinableQueue:
        return self._queue

    def _get_status(self) -> JoinableQueue:
        return self._status

    def get_action(self) -> str:
        """Get an `action` from the queue."""
        action = self._queue.get(timeout=DAEMON_REFRESH_TIME)
        self._queue.task_done()
        return action

    @property
    def status(self) -> dict:
        """Last known status of running services."""
        value = self._status.get()
        self._status.put(value)
        self._status.task_done()
        return value

    @status.setter
    def status(self, value: dict) -> None:
        """Set the status of running services."""
        self._status.get()
        self._status.put(value)
        self._status.task_done()

    def __enter__(self) -> RefittDaemonServer:
        """Start the server."""
        self.start()
        log.info('started refittd service manager')
        return self

    def __exit__(self, *exc) -> None:
        """Shutdown the server."""
        self._status.get()  # from __init__
        self._status.task_done()
        self.shutdown()
        log.info('stopped refittd service manager')
