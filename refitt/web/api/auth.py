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

"""REFITT's REST-API authentication/authorization."""

# type annotations
from typing import Callable

# standard libs
from functools import wraps
from datetime import datetime

# external libs
from flask import request

# internal libs
from .exceptions import AuthorizationNotFound, AuthorizationInvalid
from ...database.auth import (Secret, JWT, Client, TokenExpired, TokenNotFound,
                              ClientInsufficient, ClientInvalid)


def authenticate(route: Callable[[Client], dict]) -> Callable[[Client], dict]:
    """Check key:secret authorization in request."""

    @wraps(route)
    def get_client() -> dict:
        """Lookup/validate credentials and pass to route."""
        if not request.authorization:
            raise AuthorizationNotFound('expected key:secret authorization')
        client = Client.from_key(request.authorization.username)
        secret = Secret(request.authorization.password)
        if secret != client.client_secret:
            raise AuthorizationInvalid('client secret was invalid')
        return route(client)

    return get_client


def authenticated(route: Callable[..., dict]) -> Callable[..., dict]:
    """Check `request` headers for valid token."""

    @wraps(route)
    def get_client(*args, **kwargs) -> dict:
        """Validate token and lookup client credentials."""

        header = request.headers.get('Authorization', None)
        prefix = 'Bearer '
        if header is None or not header.startswith(prefix):
            raise TokenNotFound('expected "Authorization: Bearer <token>" in header')

        token = JWT.decrypt(header[len(prefix):].strip().encode())
        if token.exp is not None and datetime.utcnow() > token.exp:
            raise TokenExpired('token expired')

        client = Client.from_id(token.sub)
        return route(client, *args, **kwargs)

    return get_client


def authorization(level: int = None) -> Callable:
    """Validate client access and privilege level."""

    def valid(route: Callable[..., dict]) -> Callable[..., dict]:
        """Ensure client is valid."""

        @wraps(route)
        def check_access(client: Client, *args, **kwargs) -> dict:
            if not client.client_valid:
                raise ClientInvalid('access has been revoked')
            if level is not None and client.client_level > level:
                raise ClientInsufficient('access level insufficient')
            return route(client, *args, **kwargs)

        return check_access
    return valid
