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

"""Authentication and Authorization decorators."""


# type annotations
from __future__ import annotations
from typing import Callable

# standard libs
import logging
import functools
from datetime import datetime

# external libs
from flask import request

# internal libs
from ...database.model import Client
from ..token import Secret, JWT, AuthError, TokenNotFound, TokenExpired


# initialize module level logger
log = logging.getLogger(__name__)


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


def authenticate(route: Callable[[Client], dict]) -> Callable[[Client], dict]:
    """Check key:secret authorization in request."""

    @functools.wraps(route)
    def get_client() -> dict:
        """Lookup/validate credentials and pass to route."""
        if not request.authorization:
            raise AuthenticationNotFound('Missing key:secret in header')
        try:
            client = Client.from_key(request.authorization.username)
        except Client.NotFound:
            raise AuthenticationInvalid('Client key invalid')
        try:
            secret = Secret(request.authorization.password)
        except ValueError:  # NOTE: expected 64 digits
            raise AuthenticationInvalid('Client secret invalid')
        if secret.hashed().value != client.secret:
            raise AuthenticationInvalid('Client secret invalid')
        if not client.valid:
            raise PermissionDenied('Access has been revoked')
        return route(client)

    return get_client


def authenticated(route: Callable[..., dict]) -> Callable[..., dict]:
    """Check `request` headers for valid token."""

    @functools.wraps(route)
    def get_client(*args, **kwargs) -> dict:
        """Validate token and lookup client credentials."""
        header = request.headers.get('Authorization', None)
        prefix = 'Bearer '
        if header is None or not header.startswith(prefix):
            raise TokenNotFound('Expected "Authorization: Bearer <token>" in header')
        token = JWT.decrypt(header[len(prefix):].strip().encode())
        if token.exp is not None and datetime.now() > token.exp:
            raise TokenExpired('Token expired')
        client = Client.from_id(token.sub)
        if not client.valid:
            raise PermissionDenied('Access has been revoked')
        return route(client, *args, **kwargs)

    return get_client


def authorization(level: int = None) -> Callable:
    """Validate client access and privilege level."""

    def valid(route: Callable[..., dict]) -> Callable[..., dict]:
        """Ensure client is valid."""

        @functools.wraps(route)
        def check_access(client: Client, *args, **kwargs) -> dict:
            if level is not None and client.level > level:
                raise PermissionDenied('Authorization level insufficient')
            return route(client, *args, **kwargs)

        return check_access

    return valid
