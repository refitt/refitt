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
import json
import functools
import subprocess

# internal libs
from .... import database
from ....database import auth, user, data, recommendation as rec
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, SYSLOG_HANDLER, HOSTNAME
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
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


@application.route('/auth', methods=['GET', 'POST'])
def route_auth() -> Response:
    """
    Request for a user's most recent valid credentials (GET) or create a new set
    of credentials (POST).

    Arguments
    ---------
    auth_key: str
        The level-0 16-bit cryptographic key.

    auth_token: str
        The level-0 64-bit cryptographic token.

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
                'query': {'endpoint': '/auth',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))
        user_id = int(args.pop('user_id'))

        if args:
            raise ValueError('Invalid parameters.', list(args.keys()))

        # persistent database connection
        database.connect()

        # query database for credentials
        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials.')

        if request.method == 'GET':
            # query for user credentials
            user_auth = auth.from_user(user_id)
            if user_auth.empty:
                raise ValueError(f'No valid credentials for userid={user_id}.')

            # most recent valid credentials
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


@application.route('/profile/user', methods=['GET', 'POST'])
def route_profile_user() -> Response:
    """
    Request for a user's profile (GET) or update (POST).

    Arguments
    ---------
    auth_key: str
        The level-0 16-bit cryptographic key.

    auth_token: str
        The level-0 64-bit cryptographic token.

    user_alias: int
        The user_alias for the user whose profile is being requested.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/profile/user',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))
        alias = str(args.pop('user_alias'))

        if args:
            raise ValueError('Invalid parameters.', list(args.keys()))

        # persistent database connection
        database.connect()

        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials.')

        if request.method == 'GET':
            profile = user.get_profile(user_alias=alias)

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


@application.route('/profile/facility', methods=['GET', 'POST'])
def route_profile_facility() -> Response:
    """
    Request for a facility's profile (GET) or update (POST).

    Arguments
    ---------
    auth_key: str
        The level-0 16-bit cryptographic key.

    auth_token: str
        The level-0 64-bit cryptographic token.

    facility_name: int
        The facility name for the profile being requested.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/profile/facility',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))
        facility_name = str(args.pop('facility_name'))

        if args:
            raise ValueError('Invalid parameters.', list(args.keys()))

        # persistent database connection
        database.connect()

        if not auth.check_valid(key, token, 0):
            raise ValueError('Invalid level-0 credentials.')

        if request.method == 'GET':
            profile = user.get_facility(facility_name=facility_name)

        elif request.method == 'POST':
            # create the user profile and then re-retrieve it
            profile = dict(request.json)  # FIXME: check keys?
            user.set_facility(profile)
            profile = user.get_facility(facility_name=profile['facility_name'])

        # NOTE: the facility_id may be a `numpy.int`, we must coerce it back to a regular
        # python integer so that it can be serialized.
        response['data'] = {'facility_id': int(profile['facility_id']),
                            **profile['facility_profile']}

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


@application.route('/data/object', methods=['GET'])
def route_data_object() -> Response:
    """
    Request for an object.

    Arguments
    ---------
    auth_key: str
        The user's 16-bit cryptographic key.

    auth_token: str
        The user's 64-bit cryptographic token.

    object_id: int
        The unique object ID.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/data/object',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))
        object_id = str(args.pop('object_id'))

        if args:
            raise ValueError('Invalid parameters.', list(args.keys()))

        # persistent database connection
        database.connect()

        # FIXME: what level is sufficient?
        if not auth.check_valid(key, token, 5):
            raise ValueError('Invalid credentials.')

        table = data['observation']['object']
        query = table.select(set_index=False, join=True, where=[f'object_id={object_id}'])

        if query.empty:
            raise ValueError(f'No records found for object_id={object_id}')
        if len(query) > 1:
            raise ValueError(f'Found multiple record for object_id={object_id}')

        object_data = dict(query.iloc[0])
        response['data'] = {'object_id': int(object_data.pop('object_id')), **object_data}

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


@application.route('/recommend', methods=['GET'])
def route_recommend() -> Response:
    """
    Request for a user's recommendation(s).

    Arguments
    ---------
    auth_key: str
        The user's 16-bit cryptographic key.

    auth_token: str
        The user's 64-bit cryptographic token.

    lmag: float (optional)
        The limiting magnitude recommendations.

    limit: int (default: 1)
        The number of recommendations to return.

    group_id: int (optional)
        The recommendation_group_id. Defaults to most recent.

    previous: int (optional)
        The recommendation_id of the previous recommended object.

    Returns
    -------
    response: JSON
        RESTful response; payload is under 'data'.
    """

    args = dict(request.args)
    response = {'status': 'success',
                'query': {'endpoint': '/recommend',
                          'method': request.method,
                          'input': request.args}}
    try:
        # required query parameters
        key = str(args.pop('auth_key'))
        token = str(args.pop('auth_token'))

        # persistent database connection
        database.connect()

        # get user_id
        user_auths = auth.from_key(key)
        if user_auths.empty:
            raise ValueError(f'No valid credentials for auth_key={key}')
        elif token not in user_auths.auth_token.values:
            raise ValueError(f'Invalid token for auth_key={key}')
        user_id = user_auths.iloc[0].user_id

        # limiting magnitude (optional)
        lmag = args.pop('lmag', None)
        if lmag is not None:
            lmag = float(lmag)

        # number of recommendations to return
        limit = args.pop('limit', None)
        if limit is not None:
            limit = int(limit)

        # recommendation group (optional)
        group = args.pop('group', None)
        if group is not None:
            group = int(group)

        # recommendation group (optional)
        previous = args.pop('previous', None)
        if previous is not None:
            previous = int(previous)

        if args:
            raise ValueError('Invalid parameters.', list(args.keys()))

        # query for targets and build conditional statement
        objects = rec.get(user_id=user_id, group_id=group, limit=limit, previous=previous)
        response['data'] = objects.T.to_dict()

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
PROGRAM = f'{__appname__} service webapi'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} {{start}} [--bind ADDR] [--port INT] [--workers INT]
       {PADDING} [--certfile PATH --keyfile PATH]
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
    --keyfile   PATH    SSL keyf file.
-d, --debug             Show debugging messages.
-v, --verbose           Show information messages.
    --syslog            Use syslog style messages.
-h, --help              Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger.with_name('.'.join(PROGRAM.split()))


class WebAPI(Application):
    """Start the REFITT API server."""

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str = 'start'
    interface.add_argument('action', choices=('start', ))

    bind: str = '0.0.0.0'
    interface.add_argument('-b', '--bind', default=bind)

    port: int = 5000
    interface.add_argument('-p', '--port', type=int, default=port)

    workers: int = 2
    interface.add_argument('-w', '--workers', type=int, default=workers)

    certfile: str = None
    interface.add_argument('--certfile', default=None)

    keyfile: str = None
    interface.add_argument('--keyfile', default=None)

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

        log.info(f'starting API server [{HOSTNAME}:{self.port}] with {self.workers} workers')

        cert_ops = []
        if self.keyfile and self.certfile:
            log.info(f'cert={self.certfile} key={self.keyfile}')
            cert_ops = ['--certfile', self.certfile, '--keyfile', self.keyfile]

        cmd = ['gunicorn', '--bind', f'{self.bind}:{self.port}', '--workers', f'{self.workers}']
        cmd += cert_ops + ['refitt.apps.refitt.service.webapi']
        subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)

    def __enter__(self) -> WebAPI:
        """Initialize resources."""

        if ((self.certfile is None and self.keyfile is not None) or
           ( self.certfile is not None and self.keyfile is None)):
            raise ArgumentError('--certfile and --keyfile must be specified together.')

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
