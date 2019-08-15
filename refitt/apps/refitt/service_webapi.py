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

"""REST API server for refitt database queries."""

# standard libs
import os
import io
import sys
import json
import subprocess

# internal libs
from ...core.logging import logger
from ...core.config import config
from ...database.client import DatabaseClient, ServerAddress, UserAuth
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface
from flask import Flask as FlaskServer
from pandas import DataFrame, read_sql


# program name is constructed from module file name
NAME = os.path.basename(__file__).strip('.py').replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{start}} [--port INT] [--workers INT]
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

arguments:
start                          Start the server.

options:
-p, --port      INT            Port number for server.
-w, --workers   INT            Number of concurrent workers.
-h, --help                     Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = logger.with_name(f'{__appname__}.{NAME}')

# flask application
application = FlaskServer(__name__)


@application.route('/', methods=['GET'])
def index() -> str:
    return json.dumps({'status': 'ok', })

@application.route('/observation/object_type', methods=['GET'])
def observation_object_type() -> str:
    """Query database for observation records."""

    from ...database import observation
    from io import StringIO

    buffer = StringIO()
    observation.object_types.to_json(buffer, orient='records')
    return buffer.getvalue()



class WebAPIApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 2
    interface.add_argument('-w', '--workers', type=int, default=workers)

    def run(self) -> None:
        """Run Refitt pipeline."""
        log.info(f'starting web-api on port {self.port} with {self.workers} workers')
        subprocess.run(['gunicorn', '--bind', f'0.0.0.0:{self.port}', '--workers', f'{self.workers}',
                        'refitt.apps.refitt.service_webapi'], stdout=sys.stdout, stderr=sys.stderr)


# inherit docstring from module
WebAPIApp.__doc__ = __doc__
