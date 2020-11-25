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

"""REFITT's REST-API implementation."""

# type annotations
from __future__ import annotations
from typing import Dict, Type, Callable

# standard libs
import json
import logging
from functools import wraps

# external libs
from flask import Response, request

# internal libs
from ...database.model import NotFound
from ..token import TokenNotFound, TokenInvalid, TokenExpired
from .auth import AuthenticationNotFound, AuthenticationInvalid, PermissionDenied


# initialize module level logger
log = logging.getLogger(__name__)


# NOTE: codes and notes from Wikipedia (2020-05-08)
# https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
STATUS = {
    'OK':                            200,  # standard success
    'Created':                       201,  # resource created
    'No Content':                    204,  # note response body
    'Bad Request':                   400,  # TokenNotFound, TokenInvalid, AuthorizationNotFound, DataNotFound, BadData
    'Unauthorized':                  401,  # TokenExpired, ClientNotFound
    'Forbidden':                     403,  # ClientInvalid, ClientInsufficient, AuthorizationInvalid
    'Not Found':                     404,  # route undefined
    'Payload Too Large':             413,  # TODO: limit allowed response size?
    'I\'m a teapot':                 418,  # TODO: awesome Easter egg potential?
    'Too Many Requests':             429,  # TODO: rate limiting?
    'Unavailable For Legal Reasons': 451,  # um... what?
    'Internal Server Error':         500,  # uncaught exceptions
    'Not Implemented':               501,  # future routes
    'Service Unavailable':           503,  # TODO: keep api up but disable actions?
}


class WebException(Exception):
    """Generic to miscellaneous web exceptions."""


class PayloadTooLarge(WebException):
    """The requested or posted data was too big."""


RESPONSE_MAP: Dict[Type[Exception], int] = {
    TokenNotFound:            STATUS['Bad Request'],
    AuthenticationNotFound:   STATUS['Bad Request'],
    TokenInvalid:             STATUS['Forbidden'],
    AuthenticationInvalid:    STATUS['Forbidden'],
    PermissionDenied:         STATUS['Unauthorized'],
    TokenExpired:             STATUS['Unauthorized'],
    NotFound:                 STATUS['Not Found'],
    NotImplementedError:      STATUS['Not Implemented'],
    PayloadTooLarge:          STATUS['Payload Too Large'],
}


def endpoint(route: Callable[..., dict]) -> Callable[[...], dict]:
    """Format response."""

    @wraps(route)
    def formatted_response(*args, **kwargs) -> dict:
        status = STATUS['OK']
        response = {'status': 'success'}
        try:
            response['response'] = route(*args, **kwargs)
        except Exception as error:
            if type(error) in RESPONSE_MAP:
                response['status'] = 'error'
                response['message'] = str(error)
                status = RESPONSE_MAP[type(error)]
            else:
                response['status'] = 'critical'
                response['message'] = str(error)
                status = STATUS['Internal Server Error']
        finally:
            log.info(f'{request.method} {request.path} {status}')
            return Response(json.dumps(response), status=status,
                            mimetype='application/json')

    return formatted_response
