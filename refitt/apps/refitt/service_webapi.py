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

# type annotations
from __future__ import annotations

# standard libs
import os
import sys
import json
import functools
import subprocess

# internal libs
from ...database import auth, user
from ...core.exceptions import log_and_exit
from ...core.logging import Logger, SYSLOG_HANDLER
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application, exit_status
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
            raise ValueError('Invalid parameters.', list(args.keys()))

        # query database for credentials
        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials.')

        if request.method == 'GET':
            # query for user credentials
            user_auth = auth.from_user(user_id)
            if user_auth.empty:
                raise ValueError(f'No valid credentials for userid={user_id}.')
            # most recent credentials
            user_auth = user_auth.iloc[0].to_dict()

        elif request.method == 'POST':
            user_auth = auth.gen_auth(user_id, level=2)  # FIXME: default level for new auth?
            auth.put_auth(user_auth)

        # NOTE: `numpy` types are not serializable by `json` (ergo, must be coerced back to Python types)
        response['data'] = {'auth_level': int(user_auth['auth_level']),
                            'auth_key': str(user_auth['auth_key']),
                            'auth_token': str(user_auth['auth_token']),
                            'auth_valid': bool(user_auth['auth_valid']),
                            'auth_time': str(user_auth['auth_time']),
                            'user_id': int(user_auth['user_id'])}

    except KeyError as error:
        response['status'] = 'error'
        response['message'] = f'Missing parameter: "{error.args[0]}".'

    except ValueError as error:
        response['status'] = 'error'
        response['message'] = error.args

    except Exception as error:
        response['status'] = 'critical'
        response['message'] = error.args

    finally:
        return Response(json.dumps(response), status=200,
                        mimetype='application/json')


@application.route('/user/user', methods=['GET', 'POST'])
def route_user_user() -> Response:
    """
    Request for a user's profile (GET) or update (POST).

    Arguments
    ---------
    auth_key: str
        The 16-bit cryptographic key for the level-0 account.

    auth_token: str
        The 64-bit cryptographic token for the level-0 account.

    user_alias: int
        The user_alias for the user whose profile is being requested.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/user/user',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))

        # query database for credentials
        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials.')

        if request.method == 'GET':

            user_args = {'user_id', 'user_email', 'user_alias'}
            if len(args) < 1:
                raise ValueError(f'At least one of {user_args} required')
            elif len(args) > 1:
                raise ValueError(f'Too many arguments, expected one of {user_args}.')
            else:
                for arg in args:
                    if arg not in user_args:
                        raise ValueError(f'"{arg}" is not a valid, expected one of {user_args}.')

            if 'user_id' in args:
                profile = user.get_profile(user_id=int(args['user_id']))
            else:
                profile = user.get_profile(**args)

        elif request.method == 'POST':
            # create the user profile and then re-retrieve it
            profile = dict(request.json)
            user.set_profile(profile)
            profile = user.get_profile(user_alias=profile['user_alias'])

        # NOTE: the user_id may be a `numpy.int`, we must coerce it back to a regular
        # python integer so that it can be serialized.
        response['data'] = {'user_id': int(profile['user_id']), **profile['user_profile']}

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


# program name is constructed from module file name
NAME = os.path.basename(__file__).strip('.py').replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{start}} [--port INT] [--workers INT]
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
-p, --port      INT     Port number for server.
-w, --workers   INT     Number of concurrent workers.
-d, --debug             Show debugging messages.
-v, --verbose           Show information messages.
    --syslog            Use syslog style messages.
-h, --help              Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger.with_name(f'{__appname__}.{NAME}')


class WebAPIApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 2
    interface.add_argument('-w', '--workers', type=int, default=workers)

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
        log.info(f'starting web-api on port {self.port} with {self.workers} workers')
        subprocess.run(['gunicorn', '--bind', f'0.0.0.0:{self.port}', '--workers', f'{self.workers}',
                        'refitt.apps.refitt.service_webapi'], stdout=sys.stdout, stderr=sys.stderr)

    def __enter__(self) -> WebAPIApp:
        """Initialize resources."""

        if self.syslog:
            log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        elif self.verbose:
            log.handlers[0].level = log.levels[1]
        else:
            log.handlers[0].level = log.levels[2]

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""


# inherit docstring from module
WebAPIApp.__doc__ = __doc__