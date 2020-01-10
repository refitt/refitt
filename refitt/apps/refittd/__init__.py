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

"""Start the REFITT daemon."""

# type annotations
from __future__ import annotations
from typing import List, Dict, Tuple


# standard libs
import os
import sys
from queue import Empty

# internal libs
from .service import Service
from .server import RefittDaemonServer
from...core.config import get_config, ConfigurationError, Namespace
from...core.logging import Logger, SYSLOG_HANDLER
from...__meta__ import (__appname__, __version__, __copyright__,
                        __developer__, __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError


PROGRAM = f'{__appname__}d'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} [SERVICE [SERVICE...] | --all]
       {PADDING} [--help] [--version]

{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

arguments
SERVICE                Name of service to launch.

options:
    --all              Launch all services from configuration.
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

{EPILOG}\
"""

# initialize module level logger
log = Logger.with_name(PROGRAM)


class RefittDaemon(Application):
    """Application class for the refitt daemon, `refittd`."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('-v', '--version', version=__version__, action='version')

    all_services: bool = False
    services_requested: List[str] = []
    interface.add_argument('services_requested', nargs='*', default=services_requested)
    interface.add_argument('--all', action='store_true', dest='all_services')

    keep_alive_mode: bool = False
    interface.add_argument('--keep-alive', action='store_true', dest='keep_alive_mode')

    # NOTE: debugging messages are always shown for services.
    #       debugging messages for the daemon internals are optional.
    debug: bool = False
    interface.add_argument('--debug', action='store_true')

    # dictionary of running services
    services: Dict[str, Service] = {}

    # allowed action requests
    actions: Tuple[str] = ('restart', 'update', 'flush')

    def run(self) -> None:
        """Start the refitt service daemon."""

        config = self.get_config()
        if not self.services_requested:
            self.services_requested = list(config)
        else:
            for service in self.services_requested:
                if service not in config:
                    raise ArgumentError(f'"{service}" not found')

        for name in self.services_requested:
            self.services[name] = Service(name, **config[name])
            self.services[name].start()

        with RefittDaemonServer() as daemon:
            while True:
                try:
                    action = daemon.get_action()
                    if action == 'shutdown':
                        break
                    elif action == 'status':
                        daemon.status = self.status()
                    elif action in self.actions:
                        task = getattr(self, action)
                        task()
                    else:
                        log.error(f'action "{action}" not recognized!')
                except Empty:
                    if self.keep_alive_mode:
                        self.keep_alive()

    def keep_alive(self) -> None:
        """Ensure services are running."""
        for name, service in self.services.items():
            if not service.is_alive:
                log.error(f'"{name}" service has died - relaunching now!')
                service.restart()

    def status(self) -> dict:
        """Update the status for running services."""
        return {name: {'pid': service.pid,
                       'alive': service.is_alive,
                       'pidfile': service.pidfile,
                       'argv': service.argv,
                       'cwd': service.cwd}
                for name, service in self.services.items()}

    def flush(self) -> None:
        """Does nothing, used to flush actions and ensure ordering."""
        pass

    def restart(self) -> None:
        """Restart all services."""
        for name, service in self.services.items():
            service.restart()

    def update(self) -> None:
        """Check configuration and restart services as necessary."""
        config = self.get_config()
        for name in self.services:
            if name in config:
                self.update_service(name, config[name])
            elif self.all_services:
                log.info(f'"{name}" removed from config - stopping')
                service = self.services.pop(name)
                service.stop()
            else:
                log.warning(f'"{name}" not found in config!')
        if self.all_services:
            for name in config:
                if name not in self.services:
                    log.info(f'"{name}" service found in config')
                    self.services[name] = Service(name, **config[name])
                    self.services[name].start()

    def update_service(self, name: str, config: Namespace) -> None:
        """Update a service if necessary based on `config`."""
        for field, config_value in config.items():
            try:
                current_value = getattr(self.services[name], field)
                if current_value != config_value:
                    log.info(f'"{name}"::{field} changed - restarting!')
                    self.services[name].stop()
                    self.services[name] = Service(name, **config[name])
                    self.services[name].start()
            except AttributeError:
                pass

    def get_config(self) -> Dict[str, Namespace]:
        """Load services from configuration."""
        config = get_config()
        try:
            services = config['daemon']
        except KeyError:
            raise ConfigurationError('no services found in configuration')

        return {name: Namespace({'cwd': os.getcwd(), **services[name]})
                for name in services}

    def __enter__(self) -> RefittDaemon:
        """Initialize resources."""

        if not self.services_requested and not self.all_services:
            raise ArgumentError('no services specified')

        if self.services_requested and self.all_services:
            raise ArgumentError('specified named AND --all is redundant')

        log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        else:
            log.handlers[0].level = log.levels[1]

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        log.info('stopping services')
        for name, service in self.services.items():
            service.stop()


def main() -> int:
    """Entry-point for `refittd` console application."""
    return RefittDaemon.main(sys.argv[1:])
