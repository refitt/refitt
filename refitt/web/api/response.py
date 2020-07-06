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
from typing import Callable

# standard libs
import json
from functools import wraps

# external libs
from flask import Response, request

# internal libs
from .exceptions import DataNotFound, BadData, AuthorizationNotFound, AuthorizationInvalid, PermissionDenied
from ...database.profile import UserNotFound, FacilityNotFound
from ...database.recommendation import RecommendationNotFound
from ...database.auth import (TokenNotFound, TokenInvalid, TokenExpired,
                              ClientInvalid, ClientInsufficient, ClientNotFound)


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


def restful(route: Callable[..., dict]) -> Response:
    """Format response."""

    @wraps(route)
    def formatted_response(*args, **kwargs) -> dict:
        status = STATUS['OK']
        response = {'status': 'success'}
        try:
            response['response'] = route(*args, **kwargs)

        except (TokenNotFound, AuthorizationNotFound, DataNotFound, BadData) as error:
            status = STATUS['Bad Request']
            response['status'] = 'error'
            response['message'] = f'bad request: {error.args[0]}'

        except TokenInvalid as error:
            status = STATUS['Unauthorized']
            response['status'] = 'error'
            response['message'] = f'unauthorized: invalid token'

        except (TokenExpired, ClientNotFound) as error:
            status = STATUS['Unauthorized']
            response['status'] = 'error'
            response['message'] = f'unauthorized: {error.args[0]}'

        except (ClientInvalid, ClientInsufficient, AuthorizationInvalid, PermissionDenied) as error:
            status = STATUS['Forbidden']
            response['status'] = 'error'
            response['message'] = f'forbidden: {error.args[0]}'

        except AttributeError as error:
            status = STATUS['Bad Request']
            response['status'] = 'error'
            response['message'] = str(error)

        except UserNotFound:
            status = STATUS['Internal Server Error']
            response['status'] = 'error'
            response['message'] = f'user not found'

        except FacilityNotFound:
            status = STATUS['Internal Server Error']
            response['status'] = 'error'
            response['message'] = f'facility not found'

        except RecommendationNotFound:
            status = STATUS['Bad Request']
            response['status'] = 'error'
            response['message'] = f'recommendation not found'

        except NotImplementedError:
            status = STATUS['Not Implemented']
            response['status'] = 'error'
            response['message'] = 'not implemented'

        except Exception as error:  # noqa
            status = STATUS['Internal Server Error']
            message = str(error)
            response['status'] = 'critical'
            response['message'] = f'internal server error: {message}'

        finally:
            return Response(json.dumps(response), status=status,
                            mimetype='application/json')

    return formatted_response
