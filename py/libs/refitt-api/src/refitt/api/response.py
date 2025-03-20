# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""API response types."""


# type annotations
from __future__ import annotations
from typing import Tuple, Dict, Type, Callable, Union, IO

# external libs
from sqlalchemy.exc import NoResultFound as RecordNotFound

# internal libs
from refitt.core.logging import Logger
from refitt.api.token import AuthError, TokenNotFound, TokenInvalid, TokenExpired

# public interface
__all__ = ['STATUS', 'STATUS_CODE', 'WebException', 'FILE_SIZE_LIMIT',
           'NotFound', 'PayloadTooLarge', 'PayloadInvalid',
           'PermissionDenied', 'PayloadMalformed', 'PayloadNotFound', 'ConstraintViolation',
           'ParameterNotFound', 'ParameterInvalid', 'AuthenticationNotFound', 'AuthenticationInvalid',
           'RESPONSE_MAP', ]

# module logger
log = Logger.with_name(__name__)


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


# Limit on allowed file upload size
# e.g., 800M file allows single 10k-square CCD w/ 64-bit Integers
# Larger collections in size and number can be included if compressed
FILE_SIZE_LIMIT: int = 800 * 1024**2


class WebException(Exception):
    """Generic to miscellaneous web exceptions."""


class NotFound(WebException):
    """The requested resource doesn't exist."""


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


class ClientInvalid(AuthError):
    """The client credentials have been invalidated."""


class ClientInsufficient(AuthError):
    """The client authorization level is too low."""


class AuthenticationNotFound(AuthError):
    """Missing key:secret in authorization."""


class AuthenticationInvalid(AuthError):
    """Secret did not match expected value."""


class PermissionDenied(AuthError):
    """Action not permitted for current user/level."""


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
