# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Authentication and Authorization decorators."""


# type annotations
from __future__ import annotations
from typing import Callable, Optional

# standard libs
import functools
from datetime import datetime

# external libs
from flask import request
from cryptography.hazmat.primitives.constant_time import bytes_eq

# internal libs
from refitt.core.logging import Logger
from refitt.core.web.token import Secret, JWT, TokenNotFound, TokenExpired
from refitt.core.web.response import AuthenticationNotFound, AuthenticationInvalid, PermissionDenied
from refitt.database.model import Client

# public interface
__all__ = ['authenticated', 'authenticate', 'authorization']

# module logger
log = Logger.with_name(__name__)


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
        if not bytes_eq(secret.hashed().value.encode(), client.secret.encode()):
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


def authorization(level: Optional[int] = None) -> Callable:
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
