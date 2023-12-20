# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Endpoint response builder (e.g., application/json, etc)."""


# type annotations
from __future__ import annotations
from typing import Tuple, Dict, Type, Callable, Union, IO

# standard libs
import json
from functools import wraps

# external libs
from flask import Response, request, send_file

# internal libs
from refitt.core.logging import Logger
from refitt.core.web.response import STATUS, RESPONSE_MAP

# public interface
__all__ = ['endpoint', ]

# module logger
log = Logger.with_name(__name__)


def endpoint(content_type: str) -> Callable[..., Callable[..., Response]]:
    """Correctly format the response based on content-type."""

    def format_response(route: Callable[..., Union[dict, Tuple[IO, dict]]]) -> Callable[..., Response]:
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
