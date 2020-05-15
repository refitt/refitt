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

"""Service class implementation."""

# type annotations
from __future__ import annotations

# standard libs
import os
import sys
import shlex
from signal import SIGINT
from datetime import datetime, timedelta
from subprocess import Popen, TimeoutExpired

# internal libs
from ...core.config import get_site, VARS
from ...core.logging import Logger

# external libs
from cmdkit.cli import ArgumentError


# initialize logger
log = Logger(__name__)


class Service:
    """A subprocess of the REFITT daemon."""

    name: str = None
    argv: str = None
    cwd: str = None
    started: datetime = None
    process: Popen = None

    def __init__(self, name: str, argv: str, cwd: str = os.getcwd()) -> None:
        """Initialize directly."""
        self.name = name
        self.argv = argv
        self.cwd = cwd

    def start(self) -> None:
        """Start service."""
        if not self.is_locked:
            log.info(f'starting "{self.name}" service')
            self.process = Popen(['refitt', 'service', *shlex.split(self.argv), '--debug', '--syslog'],
                                 stdout=sys.stdout, stderr=sys.stderr, cwd=self.cwd)
            self.started = datetime.now()
            self.lock()
        else:
            raise ArgumentError(f'"{self.name}" service is already running (pid={self.pid})')

    def stop(self) -> None:
        """Stop the process."""
        try:
            if self.is_alive:
                log.info(f'stopping "{self.name}" service (pid={self.pid})')
                self.process.send_signal(SIGINT)
                self.process.wait(timeout=float(VARS['DAEMON_INTERRUPT_TIMEOUT']))
        except TimeoutExpired:
            log.error('interrupt failed for "{self.name}" (pid={self.pid}) - terminating now!')
            try:
                self.process.terminate()
                self.process.wait(timeout=float(VARS['DAEMON_INTERRUPT_TIMEOUT']))
            except TimeoutExpired:
                log.critical('terminate failed for "{self.name}" (pid={self.pid})!')
        finally:
            self.unlock()

    def restart(self) -> None:
        """Restart the process."""
        self.stop()
        self.start()

    @property
    def pidfile(self) -> str:
        """Path to pidfile for this service."""
        site = get_site()
        return os.path.join(site['run'], f'refittd.{self.name}.pid')

    @property
    def pid(self) -> int:
        """Return the PID of the current pidfile."""
        return None if self.process is None else self.process.pid

    @property
    def is_locked(self) -> bool:
        """Is the pidfile present."""
        return os.path.exists(self.pidfile)

    def lock(self) -> None:
        """Create the pidfile with the running process pid."""
        with open(self.pidfile, mode='w') as pidfile:
            print(self.process.pid, file=pidfile)

    def unlock(self) -> None:
        """Remove the pidfile."""
        try:
            os.remove(self.pidfile)
        except FileNotFoundError:
            log.warning(f'{self.pidfile} does not exist!')

    @property
    def uptime(self) -> timedelta:
        """Time since started."""
        if not self.started:
            return timedelta(seconds=0)
        else:
            return datetime.now() - self.started

    @property
    def is_alive(self) -> bool:
        """Is the process still alive."""
        return self.process is not None and self.process.poll() is None

    def keep_alive(self) -> None:
        """Check state of service and restart if necessary."""
        if not self.is_alive:
            log.error(f'"{self.name}" service has died - restarting now!')
            self.restart()
        else:
            log.debug(f'keep alive - "{self.name}"')
