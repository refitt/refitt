# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Implementation of Unix double-fork method of daemonizing a process."""


# type annotations
from __future__ import annotations

# standard libs
import os
import abc
import sys
import atexit
import logging

# internal libs
from ..core.config import get_site

# public interface
__all__ = ['Daemon', ]


# initialize module level logger
log = logging.getLogger(__name__)


class Daemon(abc.ABC):
    """Abstract base class for Daemon processes."""

    @property
    def pidfile(self) -> str:
        """Path to the refitt daemon pidfile."""
        return os.path.join(get_site()['run'], 'refittd.pid')

    def daemonize(self) -> None:
        """Daemonize class. UNIX double fork mechanism."""

        if os.path.exists(self.pidfile):
            with open(self.pidfile, mode='r') as pidfile:
                pid = int(pidfile.read().strip())
                raise RuntimeError(f'already running (pid={pid})')
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # exit first parent

        except OSError as error:
            raise RuntimeError(f'failed to create first fork: {error.args}.')

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
            raise RuntimeError(f'failed to create second fork: {error.args}.')

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # automatically remove pidfile at exit
        atexit.register(self._remove_pidfile)

        # create lockfile
        pid = str(os.getpid())
        with open(self.pidfile, mode='w') as pidfile:
            pidfile.write(pid)

    def _remove_pidfile(self) -> None:
        """Remove the process ID file."""
        os.remove(self.pidfile)

    def start(self) -> None:
        """Start the daemon."""
        self.daemonize()
