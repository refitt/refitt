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

"""Daemon service manager."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Tuple

# standard libs
import os
import sys
import logging
import subprocess
from queue import Empty

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# internal libs
from ...daemon import Daemon, DaemonService, DaemonServer
from ...core.config import config as base_config, get_site, get_config, ConfigurationError, Namespace
from ...__meta__ import __version__, __copyright__, __developer__, __contact__, __website__


PROGRAM = 'refittd'
USAGE = f"""\
usage: {PROGRAM} [-h] [-v] [SERVICE [SERVICE...] | --all] [--keep-alive] [--daemon]
{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} <{__contact__}>\
"""

HELP = f"""\
{USAGE}

arguments
SERVICE                Name of service to launch.

options:
    --all              Launch all services from configuration.
    --keep-alive       Automatically relaunch services.
    --daemon           Run in daemon mode.
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

{EPILOG}\
"""


# initialize top-level daemon logger
log = logging.getLogger('refittd')


# logging setup for command-line interface
Application.log_critical = log.critical
Application.log_exception = log.exception


class RefittDaemonApp(Application, Daemon):
    """Application class for the refitt daemon, `refittd`."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('-v', '--version', version=__version__, action='version')

    all_services: bool = False
    services_requested: List[str] = []
    interface.add_argument('services_requested', nargs='*', default=services_requested)
    interface.add_argument('--all', action='store_true', dest='all_services')

    keep_alive_mode: bool = False
    interface.add_argument('--keep-alive', action='store_true', dest='keep_alive_mode')

    daemon_mode: bool = False
    interface.add_argument('--daemon', action='store_true', dest='daemon_mode')

    # dictionary of running services
    services: Dict[str, DaemonService] = {}

    # allowed action requests
    actions: Tuple[str] = ('restart', 'reload', 'flush')

    def run(self) -> None:
        """Start the refitt service daemon."""
        log.info('Started master daemon')
        self.start_services()
        self.serve_forever()

    def start_services(self) -> None:
        """Load definitions and start services."""

        if self.daemon_mode:
            self.run_daemon()

        config = self.get_config()
        if not self.services_requested:
            self.services_requested = list(config)
        else:
            for service in self.services_requested:
                if service not in config:
                    raise ArgumentError(f'Service \'{service}\' not in configuration')

        for name in self.services_requested:
            self.services[name] = DaemonService(name, **config[name])
            self.services[name].start()

    def serve_forever(self) -> None:
        """Run server and wait for actions."""
        with DaemonServer() as daemon:
            self.await_action(daemon)

    def await_action(self, daemon: DaemonServer) -> None:
        """Wait for action requests via `daemon`, issue keep_alive."""
        while True:
            try:
                action = daemon.get_action()
                if action == 'stop':
                    break
                elif action == 'status':
                    daemon.status = self.status()
                elif action in self.actions:
                    task = getattr(self, action)
                    task()
                else:
                    log.error(f'Action \'{action}\' not recognized')
            except Empty:
                if self.keep_alive_mode:
                    self.keep_alive()

    def keep_alive(self) -> None:
        """Ensure services are running."""
        for name, service in self.services.items():
            service.keep_alive()

    def status(self) -> dict:
        """Update the status for running services."""
        return {name: {'pid': service.pid,
                       'alive': service.is_alive,
                       'pidfile': service.pidfile,
                       'uptime': service.uptime,
                       'argv': service.argv,
                       'cwd': service.cwd}
                for name, service in self.services.items()}

    def flush(self) -> None:
        """Does nothing, used to flush actions and ensure ordering."""
        pass

    def restart(self) -> None:
        """Restart all services."""
        for name, service in self.services.items():
            log.info(f'Restarting {name}')
            service.restart()

    def reload(self) -> None:
        """Check configuration and restart services as necessary."""
        config = self.get_config()
        for name in list(self.services):
            if name in config:
                self.reload_service(name, config[name])
            elif self.all_services:
                log.info(f'Service \'{name}\' removed from config - stopping')
                service = self.services.pop(name)
                service.stop()
            else:
                log.warning(f'Missing \'{name}\' from config')
        if self.all_services:
            for name in config:
                if name not in self.services:
                    log.info(f'Service \'{name}\' found in config')
                    self.services[name] = DaemonService(name, **config[name])
                    self.services[name].start()

    def reload_service(self, name: str, config: Namespace) -> None:
        """Restart a service if necessary based on `config`."""
        for field, config_value in config.items():
            try:
                current_value = getattr(self.services[name], field)
                if current_value != config_value:
                    log.info(f'Service config changed ({name}::{field}) - restarting')
                    self.services[name].stop()
                    self.services[name] = DaemonService(name, **config)
                    self.services[name].start()
            except AttributeError:
                pass

    @staticmethod
    def get_config() -> Dict[str, Namespace]:
        """Load services from configuration."""
        config = get_config()
        try:
            services = config.service
        except KeyError as error:
            raise ConfigurationError('No services found in configuration') from error
        return {name: Namespace({'cwd': os.getcwd(), **params}) for name, params in services.items()}

    def run_daemon(self) -> None:
        """Run as a daemon."""
        # NOTE: A simple way of running as a daemon while also seamlessly redirecting
        #       all stderr is to subprocess with a redirect in normal mode
        self.daemonize()
        logpath = os.path.join(get_site()['log'], 'refittd.log')
        env = {**os.environ,
               'REFITT_LOGGING_FORMAT': '%(asctime)s.%(msecs)03d %(hostname)s %(levelname)-8s [%(name)s] %(msg)s',
               'REFITT_LOGGING_DATEFMT': '%Y-%m-%d %H:%M:%S',
               'REFITT_LOGGING_LEVEL': 'DEBUG' if base_config.logging.level.upper() == 'DEBUG' else 'INFO'}
        with open(logpath, mode='a') as logfile:
            subprocess.run(['refittd', '--all', '--keep-alive'], stderr=logfile, env=env)

    def __enter__(self) -> RefittDaemonApp:
        """Initialize resources."""
        if not self.services_requested and not self.all_services:
            raise ArgumentError('No services specified')
        if self.services_requested and self.all_services:
            raise ArgumentError('Passing named services AND --all is redundant')
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        # Note: daemon variant does not actually start any services in this process
        if not self.daemon_mode:
            log.info('Stopping services')
            for name, service in self.services.items():
                service.stop()


def main() -> int:
    """Entry-point for `refittd` console application."""
    return RefittDaemonApp.main(sys.argv[1:])
