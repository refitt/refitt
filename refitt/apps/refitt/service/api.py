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

"""Start API server."""


# type annotations
from __future__ import annotations

# standard libs
import os
import sys
import socket
import logging
import functools
import subprocess

# internal libs
from ....web.api import application as api
from ....core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = 'service api'
USAGE = f"""\
usage: {PROGRAM} [-h] {{start}} [-p PORT] [-w NUM] [-t SECONDS] [--dev] [...]\
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
start                    Start the server.

options:
-p, --port      NUM      Port number for server (default: 5000).
-w, --workers   NUM      Number of concurrent workers.
    --certfile  PATH     SSL certificate file.
    --keyfile   PATH     SSL key file.
-t, --timeout   SECONDS  Number of seconds for worker timeouts.
    --dev                Run in development mode.
-h, --help               Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


# global reference to hostname
HOST = socket.gethostname()


class WebApp(Application):
    """Application class for api server start-up."""

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 1
    interface.add_argument('-w', '--workers', type=int, default=workers)

    certfile: str = None
    interface.add_argument('--certfile', default=None)

    keyfile: str = None
    interface.add_argument('--keyfile', default=None)

    timeout: int = 60  # seconds
    interface.add_argument('-t', '--timeout', type=int, default=timeout)

    dev_mode: bool = False
    interface.add_argument('--dev', action='store_true', dest='dev_mode')

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Start REFITT Web-API server."""

        if ((self.certfile is None and self.keyfile is not None) or
           ( self.certfile is not None and self.keyfile is None)):
            raise ArgumentError('--certfile and --keyfile must be specified together.')

        if self.dev_mode:
            api.run('localhost', self.port, debug=True)
        else:
            self.run_gunicorn()

    def run_gunicorn(self) -> None:
        """Run the server with Gunicorn."""

        log.info(f'Starting server [{HOST}:{self.port}] with {self.workers} workers')

        cert_ops = []
        if self.keyfile and self.certfile:
            log.info(f'cert={self.certfile} key={self.keyfile}')
            cert_ops = ['--certfile', self.certfile, '--keyfile', self.keyfile]

        path = os.path.join(os.path.dirname(sys.executable), 'gunicorn')
        cmd = [path, '--bind', f'0.0.0.0:{self.port}',
               '--workers', f'{self.workers}', '--timeout', f'{self.timeout}']
        cmd += cert_ops + ['refitt.web.api']
        subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
