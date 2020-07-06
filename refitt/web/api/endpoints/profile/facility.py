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


def get(id_or_name: str) -> dict:
    """Get a facility profile."""
    return Facility.from_id_or_name(id_or_name).to_dict()


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


def put(id_or_name: str, data: dict) -> dict:
    """Alter a facility profile."""
    if not data:
        raise DataNotFound('missing facility profile data')
    try:
        profile = Facility.from_id_or_name(id_or_name)
        given_id = data.pop('facility_id', profile.facility_id)
        if given_id != profile.facility_id:
            raise BadData(f'/profile/facility/{id_or_name} does not match '
                          f'facility_id={given_id} in posted data')
        data = {'facility_id': profile.facility_id, **data}
        profile = Facility.from_dict(data)
        profile.to_database()
        return {'facility_id': profile.facility_id}
    except KeyError as error:
        raise BadData(f'missing "{error.args[0]}" in facility profile data') from error
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error


def delete(id_or_name: str) -> dict:
    """Remove a facility profile."""
    try:
        profile = Facility.from_id_or_name(id_or_name)
        Facility.remove(profile.facility_id)
        return {'facility_id': profile.facility_id}
    except DatabaseError as error:
        msgs = " - ".join(str(msg) for msg in error.args)
        raise BadData(f'database: {msgs}') from error
