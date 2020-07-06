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

"""The /profile/user end-point verbs."""

# external libs
from sqlalchemy.exc import DatabaseError

# internal libs
from ...exceptions import DataNotFound, BadData
from .....database.profile import User


def get(id_or_alias: str) -> dict:
    """Get a user profile."""
    return User.from_id_or_alias(id_or_alias).to_dict()


def post(data: dict) -> dict:
    """Add a new user profile."""
    if not data:
        raise DataNotFound('missing user profile data')
    try:
        profile = User.from_dict(data)
        user_id = profile.to_database()
        return {'user_id': user_id}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in user profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def put(id_or_alias: str, data: dict) -> dict:
    """Alter a user profile."""
    if not data:
        raise DataNotFound('missing user profile data')
    try:
        profile = User.from_id_or_alias(id_or_alias)
        given_id = data.pop('user_id', None)
        if given_id and given_id != profile.user_id:
            raise BadData(f'/profile/user/{id_or_alias} does not match user_id={given_id} in posted data')

        data = {'user_id': profile.user_id, **data}
        profile = User.from_dict(data)
        profile.to_database()
        return {'user_id': profile.user_id}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in user profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def delete(id_or_alias: str) -> dict:
    """Remove a user profile."""
    try:
        profile = User.from_id_or_alias(id_or_alias)
        User.remove(profile.user_id)
        return {'user_id': profile.user_id}
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error
