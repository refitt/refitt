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


def get(user_id: int) -> dict:
    """Get a user profile."""
    return User.from_id(user_id).to_dict()


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


def put(user_id: int, data: dict) -> dict:
    """Alter a user profile."""
    if not data:
        raise DataNotFound('missing user profile data')
    try:
        data = {'user_id': user_id, **data}
        profile = User.from_dict(data)
        profile.to_database()
        return {}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in user profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def delete(user_id: int) -> dict:
    """Remove a user profile."""
    try:
        User.remove(user_id)
        return {}
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error
