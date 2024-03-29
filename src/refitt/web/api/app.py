# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Initialize Flask application instance."""


# type annotations
from __future__ import annotations

# standard libs
import json

# external libs
from flask import Flask, Response, request

# internal libs
from refitt.core.logging import Logger
from refitt.database.interface import Session
from refitt.web.api.response import STATUS

# public interface
__all__ = ['application', ]

# module logger
log = Logger.with_name(__name__)


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
