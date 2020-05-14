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
from .....database.profile import Facility


def get(facility_id: int) -> dict:
    """Get a facility profile."""
    return Facility.from_id(facility_id).to_dict()


def post(data: dict) -> dict:
    """Add a new facility profile."""
    if not data:
        raise DataNotFound('missing facility profile data')
    try:
        profile = Facility.from_dict(data)
        facility_id = profile.to_database()
        return {'facility_id': facility_id}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in facility profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def put(facility_id: int, data: dict) -> dict:
    """Alter a facility profile."""
    if not data:
        raise DataNotFound('missing facility profile data')
    try:
        data = {'facility_id': facility_id, **data}
        profile = Facility.from_dict(data)
        profile.to_database()
        return {}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in facility profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def delete(facility_id: int) -> dict:
    """Remove a facility profile."""
    try:
        Facility.remove(facility_id)
        return {}
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error
