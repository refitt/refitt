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

"""REFITT's API /token end-point."""

# standard libs
from datetime import timedelta

# internal libs
from ....database.auth import (Client, ClientInvalid, ClientNotFound, DEFAULT_CLIENT_LEVEL,
                               Access, DEFAULT_EXPIRE_TIME)

# default access token expiration period
ACCESS_EXPIRES = timedelta(hours=DEFAULT_EXPIRE_TIME)


def get(client_id: int) -> dict:
    """Generate a new access token for a user."""
    access = Access.new_token(client_id, access_expires=ACCESS_EXPIRES)
    return access.embed()


def get_user(user_id: int) -> dict:
    """Generate a new access token on behalf of a different user."""
    try:
        user_client = Client.from_user(user_id)
    except ClientNotFound:
        user_client = Client.new(user_id, DEFAULT_CLIENT_LEVEL)
    if not user_client.client_valid:
        raise ClientInvalid(f'access revoked for user_id={user_id}')
    user_access = Access.new_token(user_client.client_id, access_expires=ACCESS_EXPIRES)
    return user_access.embed()


def get_client(user_id: int) -> dict:
    """Generate a new set of client credentials."""
    client = Client.new(user_id, DEFAULT_CLIENT_LEVEL)
    access = Access.new_token(client.client_id, access_expires=ACCESS_EXPIRES)
    return {**client.embed(), **access.embed()}
