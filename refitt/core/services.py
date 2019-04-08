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

"""Implementation of abstract base class for daemon services."""


# standard libs
import os
import sys
import time
import atexit
import signal
import abc
import multiprocessing

# internal libs
from ..__meta__ import __appname__
from .logging import get_logger


# initialize module level logger
log = get_logger(f'{__appname__}.service')


class Daemon(abc.ABC):
    """Abstract base class for Daemon processes."""

    def __init__(self, pidfile: str) -> None:
        """
        Initialization. You must call `.start()` before `.run()`.

        Arguments
        ---------
        pidfile: str
            Path to a process ID file. This file is created with
            the process ID so it can be stopped later.
        """
        self.pidfile = pidfile

    def daemonize(self) -> None:
        """Deamonize class. UNIX double fork mechanism."""

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit first parent

        except OSError as error:
            log.critical(f'{self.__class__.__name__}.daemonize: failed to create first fork. '
                         f'Error was, "{error}".')
            sys.exit(1)

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit second parent

        except OSError as error:
            log.critical(f'{self.__class__.__name__}.daemonize: failed to create second fork. '
                         f'Error was, "{error}".')
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.remove_pidfile)

        pid = str(os.getpid())
        log.info(f'writing {pid} to {self.pidfile}.')
        with open(self.pidfile, 'w+') as fh:
            fh.write(pid)

    def remove_pidfile(self) -> None:
        """Remove the process ID file."""
        os.remove(self.pidfile)

    def start(self) -> None:
        """Start the daemon."""
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if pid:
            log.error(f'{self.__class__.__name__.lower()}: {self.pidfile} already exists. '
                      f'Daemon already running at {pid}.')
            sys.exit(1)

        log.info(f'starting {self.__class__.__name__.lower()}')
        self.daemonize()
        self.run()

    def stop(self) -> None:
        """Stop the daemon."""

        # Get the pid from the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            log.error(f'{self.__class__.__name__.lower()}: {self.pidfile} does not exists. '
                      f'Daemon not running.')
            return  # not an error in a restart

        try:
            log.info(f'stopping {self.__class__.__name__.lower()}')
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)

        except OSError as error:
            err_msg = str(error.args)
            if 'no such process' in err_msg.lower():
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                log.error(f'{self.__class__.__name__.lower()}: could not stop daemon. '
                          f'Error was: "{error}"')
                sys.exit(1)

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        self.start()

    @abc.abstractmethod
    def run(self) -> None:
        """Entry point for daemon service."""
        raise NotImplementedError()


class Service(Daemon):
    """A Service can be run directly as a daemonized."""

    def __init__(self, pidfile: str, daemon: bool=False) -> None:
        """
        Initialization. You must call `.start()` before `.run()` is called.

        Arguments
        ---------
        pidfile: str
            Path to a process ID file. This file is created with
            the process ID so it can be stopped later.

        daemon: bool (default=False)
            Run service as a daemon process.
        """
        super().__init__(self.pidfile)
        self.daemon = daemon

    def daemonize(self) -> None:
        """Overrides the Daemon implementation if not `daemon`."""
        if self.daemon:
            super().daemonize()

    @property
    def daemon(self) -> bool:
        """Is this service able to become a daemon."""
        return self.__daemon

    @daemon.setter
    def daemon(self, other: bool) -> None:
        """Assign whether this service can become a daemon."""
        if other in (True, False, 0, 1):
            self.__daemon = bool(other)
        else:
            raise ValueError(f'{self.__class__.__name__}.daemon expects True/False.')


class Agent(Service):
    """An agent spawns 'task' jobs with a specified periodicity."""

    def __init__(self, pidfile: str, period: float, daemon: bool=False) -> None:
        """
        Initialize an Agent.

        Arguments
        id: str
            Unique identifier (used for runtime pid file).
        period: float
            Seconds to wait between successive tasks.
        """
        # service/daemon
        self.id = id
        super().__init__(pidfile, daemon=daemon)

        # agent attributes
        self.period = period

    @property
    def id(self) -> str:
        """Unique identifier for Agent."""
        return self.__id

    @id.setter
    def id(self, other: str) -> None:
        """Assign unique identifier for Agent."""
        value = str(other)
        for badchar in ('/', ' ', '`'):
            if badchar in value:
                raise ValueError(f'{self.__class__.__name__}.id is used to create the pidfile, ',
                                 f'it cannot contain \"{badchar}\".')
        self.__id = value

    @property
    def period(self) -> float:
        """The period the Agent sleeps between spawning tasks."""
        return self.__period

    @period.setter
    def period(self, other: float) -> None:
        """Assign the period used to sleep between spawning tasks."""
        value = float(other)
        if value <= 0:
            raise ValueError(f'{self.__class__.__name__}.period expects a positive value, '
                             f'given {value}.')
        self.__period = value

    @abc.abstractmethod
    def task(self) -> None:
        """A task must be defined for all Agents."""
        raise NotImplementedError()

    def spawn_task(self) -> multiprocessing.Process:
        """Fork a new child process to run 'task'."""
        p = multiprocessing.Process(target=self.task)
        p.start()
        log.debug(f'{self.__class__.__name__}: new task started at {p.pid}.')
        return p

    def run(self) -> None:
        """An Agent spawns 'task' jobs with a specified sleep period."""
        task = self.spawn_task()
        while True:
            time.sleep(self.period)
            if task.is_alive():
                log.warning(f'{self.__class__.__name__}:{self.id}: task not finished '
                            f'at {task.pid}, waiting...')
            task.join()
            task = self.spawn_task()
