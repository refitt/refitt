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
from typing import Tuple, Dict, Type, Callable, Union, IO

# standard libs
import json
import logging
from functools import wraps

# external libs
from flask import Response, request, send_file

# internal libs
from ...database.model import NotFound as RecordNotFound
from ..token import TokenNotFound, TokenInvalid, TokenExpired
from .auth import AuthenticationNotFound, AuthenticationInvalid, PermissionDenied


# initialize module level logger
log = logging.getLogger(__name__)


# NOTE: codes and notes from Wikipedia (2020-05-08)
# https://en.wikipedia.org/wiki/List_of_HTTP_status_codes
STATUS = {
    'OK':                            200,
    'Created':                       201,
    'No Content':                    204,
    'Bad Request':                   400,
    'Unauthorized':                  401,
    'Forbidden':                     403,
    'Not Found':                     404,
    'Method Not Allowed':            405,
    'Payload Too Large':             413,
    'I\'m a teapot':                 418,  # TODO: awesome Easter egg potential?
    'Too Many Requests':             429,  # TODO: rate limiting?
    'Unavailable For Legal Reasons': 451,  # um... what?
    'Internal Server Error':         500,  # uncaught exceptions
    'Not Implemented':               501,  # future routes
    'Service Unavailable':           503,  # TODO: keep api up but disable actions?
}


# reversed mapping
STATUS_CODE = {code: name for name, code in STATUS.items()}


class WebException(Exception):
    """Generic to miscellaneous web exceptions."""


class NotFound(WebException):
    """The requested resource doesn't exist.."""


class PayloadTooLarge(WebException):
    """The requested or posted data was too big."""


class PayloadNotFound(WebException):
    """Expected data in the payload and didn't find any."""


class PayloadMalformed(WebException):
    """Expected a particular type of data (i.e., JSON) in the payload."""


class PayloadInvalid(WebException):
    """The contents of the payload did not meet some content-specific requirement."""


class ConstraintViolation(WebException):
    """The request violated some constraint or integrity within the data model."""


class ParameterNotFound(WebException):
    """The URL parameter was not provided but was required."""


class ParameterInvalid(WebException):
    """The URL parameter is not valid for the requested endpoint."""


RESPONSE_MAP: Dict[Type[Exception], int] = {
    TokenNotFound:            STATUS['Forbidden'],
    AuthenticationNotFound:   STATUS['Forbidden'],
    TokenInvalid:             STATUS['Forbidden'],
    AuthenticationInvalid:    STATUS['Forbidden'],
    TokenExpired:             STATUS['Forbidden'],
    PermissionDenied:         STATUS['Unauthorized'],
    RecordNotFound:           STATUS['Not Found'],
    NotFound:                 STATUS['Not Found'],
    PayloadNotFound:          STATUS['Bad Request'],
    PayloadMalformed:         STATUS['Bad Request'],
    PayloadInvalid:           STATUS['Bad Request'],
    ConstraintViolation:      STATUS['Bad Request'],
    ParameterNotFound:        STATUS['Bad Request'],
    ParameterInvalid:         STATUS['Bad Request'],
    NotImplementedError:      STATUS['Not Implemented'],
    PayloadTooLarge:          STATUS['Payload Too Large'],
}


EndpointDecorator = Callable[..., Response]
def endpoint(content_type: str) -> Callable[..., EndpointDecorator]:
    """Correctly format the response based on content-type."""

    def format_response(route: Callable[..., Union[dict, Tuple[IO, dict]]]) -> EndpointDecorator:
        """Dispatch based on content-type."""

        @wraps(route)
        def format_json(*args, **kwargs) -> Response:
            status = STATUS['OK']
            response = {'Status': 'Success'}
            try:
                response['Response'] = route(*args, **kwargs)
            except Exception as error:
                response['Message'] = str(error)
                for exc_type, status_code in RESPONSE_MAP.items():
                    if isinstance(error, exc_type):
                        status = status_code
                        response['Status'] = 'Error'
                        break
                else:
                    response['Status'] = 'Critical'
                    status = STATUS['Internal Server Error']
            finally:
                log.info(f'{request.method} {request.path} {status}')
                return Response(json.dumps(response), status=status,
                                mimetype='application/json')

        @wraps(route)
        def format_stream(*args, **kwargs) -> Response:
            status = STATUS['OK']
            try:
                stream, options = route(*args, **kwargs)
                return send_file(stream, mimetype='application/octet-stream', **options)
            except Exception as error:
                response = dict()
                for exc_type, status_code in RESPONSE_MAP.items():
                    if isinstance(error, exc_type):
                        status = status_code
                        response['Status'] = 'Error'
                        break
                else:
                    status = STATUS['Internal Server Error']
                    response['Status'] = 'Critical'
                response['Message'] = str(error)
                return Response(json.dumps(response), status=status,
                                mimetype='application/json')
            finally:
                log.info(f'{request.method} {request.path} {status}')

        @wraps(route)
        def content_type_not_implemented(*args, **kwargs) -> Response:  # noqa: unused arguments
            return Response(json.dumps({'Status': 'Critical',
                                        'Message': f'Content-type not defined: \'{content_type}\''}),
                            mimetype='application/json', status=STATUS['Internal Server Error'])

        if content_type == 'application/json':
            return format_json

        if content_type == 'application/octet-stream':
            return format_stream

        return content_type_not_implemented

    return format_response
