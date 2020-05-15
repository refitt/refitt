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

"""Start the REFITT API server."""

# type annotations
from __future__ import annotations

# standard libs
import sys
import functools
import subprocess

# internal libs
from ....web.api import application as api
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup, HOSTNAME
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = f'{__appname__} service webapi'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{start}} [--bind ADDR] [--port INT] [--workers INT]
       {PADDING} [--dev] [--certfile PATH --keyfile PATH]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

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

arguments:
start                   Start the server.

options:
-p, --port      INT     Port number for server (default: 5000).
-b, --bind      ADDR    Bind address (default: 0.0.0.0).
-w, --workers   INT     Number of concurrent workers.
    --certfile  PATH    SSL certificate file.
    --keyfile   PATH    SSL key file.
    --dev               Run in development mode.
-d, --debug             Show debugging messages.
-v, --verbose           Show information messages.
    --syslog            Use syslog style messages.
-h, --help              Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger(__name__)


class WebAPI(Application):
    """Start the REFITT API server."""

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    bind: str = '0.0.0.0'
    interface.add_argument('-b', '--bind', default=bind)

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 1
    interface.add_argument('-w', '--workers', type=int, default=workers)

    certfile: str = None
    interface.add_argument('--certfile', default=None)

    keyfile: str = None
    interface.add_argument('--keyfile', default=None)

    dev_mode: bool = False
    interface.add_argument('--dev', action='store_true', dest='dev_mode')

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Start REFITT Web-API server."""
        if self.dev_mode:
            api.run(self.bind, self.port, debug=True)
        else:
            self.run_gunicorn()

    def run_gunicorn(self) -> None:
        """Run the server with Gunicorn."""

        log.info(f'starting API server [{HOSTNAME}:{self.port}] with {self.workers} workers')

        cert_ops = []
        if self.keyfile and self.certfile:
            log.info(f'cert={self.certfile} key={self.keyfile}')
            cert_ops = ['--certfile', self.certfile, '--keyfile', self.keyfile]

        cmd = ['gunicorn', '--bind', f'{self.bind}:{self.port}', '--workers', f'{self.workers}']
        cmd += cert_ops + ['refitt.web.api']
        subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)

    def __enter__(self) -> WebAPI:
        """Initialize resources."""

        if ((self.certfile is None and self.keyfile is not None) or
           ( self.certfile is not None and self.keyfile is None)):
            raise ArgumentError('--certfile and --keyfile must be specified together.')

        cli_setup(self)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
