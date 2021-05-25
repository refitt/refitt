# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""The Daemon service manager."""


# type annotations
from __future__ import annotations

# standard libs
import logging
from multiprocessing import JoinableQueue
from multiprocessing.managers import BaseManager

# internal libs
from ..core.config import config

# public interface
__all__ = ['DaemonServer', ]


# initialize module level logger
log = logging.getLogger(__name__)


# time between keep alive requests (seconds)
DAEMON_REFRESH_TIME = float(config.daemon.refresh)


class DaemonServer(BaseManager):
    """Serve managed queue of actions."""

    _queue: JoinableQueue = None
    _status: JoinableQueue = None

    def __init__(self) -> None:
        """Initialize the queue."""
        super().__init__(address=('localhost', int(config.daemon.port)), authkey=config.daemon.key.encode())
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

    def __enter__(self) -> DaemonServer:
        """Start the server."""
        self.start()
        log.info('Started daemon server')
        return self

    def __exit__(self, *exc) -> None:
        """Shutdown the server."""
        self._status.get()  # from __init__
        self._status.task_done()
        self.shutdown()
        log.info('Stopped daemon server')
