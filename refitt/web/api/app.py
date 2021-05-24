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

"""Initialize Flask application instance."""


# type annotations
from __future__ import annotations

# standard libs
import json
import logging

# external libs
from flask import Flask, Response, request

# internal libs
from .response import STATUS
from ...database.core import Session

# public interface
__all__ = ['application', ]


# initialize module level logger
log = logging.getLogger(__name__)


# flask application
application = Flask(__name__)


@application.errorhandler(STATUS['Not Found'])
def not_found(error) -> Response:  # noqa: unused error object
    """Response to an invalid request."""
    return Response(json.dumps({'Status': 'Error',
                                'Message': f'Not found: {request.path}'}),
                    status=STATUS['Not Found'],
                    mimetype='application/json')


@application.errorhandler(STATUS['Method Not Allowed'])
def method_not_allowed(error) -> Response:  # noqa: unused error object
    """Response to an invalid request."""
    return Response(json.dumps({'Status': 'Error',
                                'Message': f'Method not allowed: {request.method} {request.path}'}),
                    status=STATUS['Method Not Allowed'],
                    mimetype='application/json')


@application.before_request
def before_request() -> None:
    """Log start of request."""
    log.debug(f'Request started: {request.method} {request.path}')


@application.after_request
def after_request(response: Response) -> Response:
    """Finalize any transaction/rollback and log end of request."""
    Session.close()
    log.debug(f'Request finished: {request.method} {request.path} {response.status}')
    return response
