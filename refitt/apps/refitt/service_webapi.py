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
import sys
import json
import subprocess

# internal libs
from ...database import auth
from ...core.logging import logger
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface
from flask import Flask, Response, request


# flask application
application = Flask(__name__)

# response codes
STATUS = {'Ok': 200,
          'Forbidden': 403,
          'Not Found': 404,
          'Internal Server Error': 500,
          'Service Unavailable': 503}


@application.errorhandler(STATUS['Not Found'])
def not_found(error=None) -> Response:
    """Response to an invalid request."""
    response = {'status': 'Not Found', }
    return Response(json.dumps(response), status=200,
                    mimetype='application/json')


@application.route('/user/auth', methods=['GET', 'POST'])
def route_user_auth() -> Response:
    """
    Request for a user's most recent valid credentials (GET) or create a new set
    of credentials (POST).

    Arguments
    ---------
    auth_key: str
        The 16-bit cryptographic key for the level-0 account.

    auth_token: str
        The 64-bit cryptographic token for the level-0 account.

    user_id: int
        The user_id for the user whose most recent, valid credentials
        are being requested.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/user/auth',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))
        user_id = int(args.pop('user_id'))

        log.info(f'{request.method}: user_id={user_id}')

        if args:
            raise ValueError('Invalid parameters', list(args.keys()))

        # query database for credentials
        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials')

        if request.method == 'GET':
            # query for user credentials
            user = auth.from_user(user_id)
            if user.empty:
                raise ValueError(f'No valid credentials for userid={user_id}.')
            # most recent credentials
            user = user.iloc[0].to_dict()

        elif request.method == 'POST':
            user = auth.gen_auth(user_id, level=2)  # FIXME: default level for new auth?
            auth.put_auth(user)

        # NOTE: `numpy` types are not serializable by `json` (ergo, must be coerced back to Python types)
        response['data'] = {'auth_level': int(user['auth_level']),
                            'auth_key': str(user['auth_key']),
                            'auth_token': str(user['auth_token']),
                            'auth_valid': bool(user['auth_valid']),
                            'auth_time': str(user['auth_time']),
                            'user_id': int(user['user_id'])}

    except KeyError as error:
        response['status'] = 'error'
        response['message'] = f'Missing parameter: "{error.args[0]}"'

    except ValueError as error:
        response['status'] = 'error'
        response['message'] = error.args

    except Exception as error:
        response['status'] = 'critical'
        response['message'] = error.args

    finally:
        return Response(json.dumps(response), status=200,
                        mimetype='application/json')


@application.route('/observation/object_type', methods=['GET'])
def observation_object_type() -> str:
    """Query database for observation records."""


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


class WebAPIApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 2
    interface.add_argument('-w', '--workers', type=int, default=workers)

    def run(self) -> None:
        """Start REFITT Web-API server."""
        log.info(f'starting web-api on port {self.port} with {self.workers} workers')
        subprocess.run(['gunicorn', '--bind', f'0.0.0.0:{self.port}', '--workers', f'{self.workers}',
                        'refitt.apps.refitt.service_webapi'], stdout=sys.stdout, stderr=sys.stderr)


# inherit docstring from module
WebAPIApp.__doc__ = __doc__
