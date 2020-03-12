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

"""User/facility profile management."""

# type annotations
from typing import List

# standard libs
import json

# internal libs
from ..core.logging import Logger
from .interface import execute, select, insert

# external libs
from sqlalchemy.sql import text
from pandas import DataFrame


# initialize module level logger
log = Logger.with_name('refitt.database.profile')


def get_facility_map(user_id: int) -> List[int]:
    """Get list of facility_id's for `user_id` from "user"."facility_map"."""
    records = select(['facility_id'], 'user', 'facility_map', where=[f'user_id = {user_id}'])
    return list(records.facility_id)


def put_facility_map(user_id: int, facility_ids: List[int]) -> None:
    """Insert all `facility_ids` with `user_id` into "user"."facility_map"."""
    records = DataFrame({'facility_id': list(facility_ids)}).assign(user_id=user_id)
    insert(records, 'user', 'facility_map')
    log.info(f'added facilities to map: user_id={user_id}, facility_id={facility_ids}')


DELETE_FACILITY_MAP_QUERY = """\
DELETE FROM "user"."facility_map"
WHERE "user_id" = {user_id};
"""


def del_facility_map(user_id: int) -> None:
    """Remove all records from "user"."facility_map" for `user_id`."""
    execute(DELETE_FACILITY_MAP_QUERY.format(user_id=user_id))
    log.info(f'removed all facilities in map with user_id={user_id}')


def _get_user_from_id(user_id: int) -> DataFrame:
    """Get user profile from `user_id`."""
    return select([], 'user', 'user', where=[f"user_id = {user_id}"], set_index=False)


def _get_user_from_email(user_email: str) -> DataFrame:
    """Get user profile from `user_email`."""
    return select([], 'user', 'user', where=[f"user_email = '{user_email}'"], set_index=False)


def _get_user_from_alias(user_alias: str) -> DataFrame:
    """Get user profile from `user_alias`."""
    return select([], 'user', 'user', where=[f"user_alias = '{user_alias}'"], set_index=False)


_USER_GETTERS = {
    'user_id': _get_user_from_id,
    'user_email': _get_user_from_email,
    'user_alias': _get_user_from_alias
}


def get_user(**user_field) -> dict:
    """Get user profile from one of `user_id`, `user_email` or `user_alias`."""

    if len(user_field) != 1 or list(user_field.keys())[0] not in _USER_GETTERS:
        raise KeyError(f'Named parameters can only be one of {list(_USER_GETTERS.keys())}')

    for field, value in user_field.items():
        records = _USER_GETTERS[field](value)
        if records.empty:
            raise ValueError(f'No user with {field}={value}')
        profile = dict(records.iloc[0])
        return {**profile, **{'user_facilities': get_facility_map(profile['user_id'])}}


UPDATE_USER_QUERY = """\
INSERT INTO "user"."user" (user_id, user_first_name, user_last_name, user_email, user_alias, user_profile)
VALUES (:user_id, :user_first_name, :user_last_name, :user_email, :user_alias, :user_profile)
ON CONFLICT (user_id) DO UPDATE
    SET user_first_name = excluded.user_first_name,
        user_last_name  = excluded.user_last_name,
        user_email      = excluded.user_email,
        user_alias      = excluded.user_alias,
        user_profile    = excluded.user_profile;
"""


INSERT_USER_QUERY = """\
INSERT INTO "user"."user" (user_first_name, user_last_name, user_email, user_alias, user_profile)
VALUES (:user_first_name, :user_last_name, :user_email, :user_alias, :user_profile);
"""


def set_user(profile: dict) -> None:
    """
    Insert/update user profile in database.

    Arguments
    ---------
    profile: dict
        User profile dictionary to be inserted. This will be JSON serialized.
        If user_facilities (list) is provided, these will be synchronized with
        the facility_map table. If user_id is missing, a new profile will be
        created.
    """

    user_id = None if 'user_id' not in profile else int(profile['user_id'])
    log.info(f'setting user profile (user_id={user_id})')

    data = dict(user_first_name=str(profile['user_first_name']),
                user_last_name=str(profile['user_last_name']),
                user_email=str(profile['user_email']),
                user_alias=str(profile['user_alias']),
                user_profile=json.dumps(profile))

    if user_id is not None:
        del_facility_map(user_id)
        put_facility_map(user_id, set(map(int, profile.get('user_facilities', []))))
        execute(text(UPDATE_USER_QUERY), user_id=user_id, **data)
        log.info(f'updated user profile: user_id={user_id}')

    else:
        execute(text(INSERT_USER_QUERY), **data)
        log.info(f'created user profile: user_alias={profile["user_alias"]}')
        put_facility_map(get_user(user_alias=profile['user_alias'])['user_id'],
                         set(map(int, profile.get('user_facilities', []))))


UPDATE_FACILITY_QUERY = """\
INSERT INTO "user"."facility" (facility_id, facility_name, facility_latitude, facility_longitude, facility_altitude,
                               facility_limiting_magnitude, facility_profile)
VALUES (:facility_id, :facility_name, :facility_latitude, :facility_longitude, :facility_altitude,
        :facility_limiting_magnitude, :facility_profile)
ON CONFLICT (facility_id) DO UPDATE
    SET facility_name = excluded.facility_name,
        facility_latitude = excluded.facility_latitude,
        facility_longitude = excluded.facility_longitude,
        facility_altitude = excluded.facility_altitude,
        facility_limiting_magnitude = excluded.facility_limiting_magnitude,
        facility_profile = excluded.facility_profile;
"""


INSERT_FACILITY_QUERY = """\
INSERT INTO "user"."facility" (facility_name, facility_latitude, facility_longitude, facility_altitude,
                               facility_limiting_magnitude, facility_profile)
VALUES (:facility_name, :facility_latitude, :facility_longitude, :facility_altitude,
        :facility_limiting_magnitude, :facility_profile)
"""


def set_facility(profile: dict) -> None:
    """
    Insert/update facility profile in database.

    Arguments
    ---------
    profile: dict
        Facility profile dictionary to be inserted.
        This will be JSON serialized.
    """

    facility_id = None if 'facility_id' not in profile else int(profile['facility_id'])

    data = dict(facility_name=profile['facility_name'],
                facility_latitude=profile['facility_latitude'],
                facility_longitude=profile['facility_longitude'],
                facility_altitude=profile['facility_altitude'],
                facility_limiting_magnitude=profile['facility_limiting_magnitude'],
                facility_profile=json.dumps(profile))

    if facility_id is not None:
        execute(text(UPDATE_FACILITY_QUERY), facility_id=facility_id, **data)
        log.info(f'set facility profile for facility_id={facility_id}')

    else:
        facility_name = profile['facility_name']
        execute(text(INSERT_FACILITY_QUERY), **data)
        log.info(f'set facility profile for facility_name="{facility_name}"')


def _get_facility_from_id(facility_id: int) -> DataFrame:
    """Get facility profile from `facility_id`."""
    return select([], 'user', 'facility', where=[f"facility_id = {facility_id}"], set_index=False)


def _get_facility_from_name(facility_name: str) -> DataFrame:
    """Get facility profile from `facility_name`."""
    return select([], 'user', 'facility', where=[f"facility_name = '{facility_name}'"], set_index=False)


_FACILITY_GETTERS = {
    'facility_id': _get_facility_from_id,
    'facility_name': _get_facility_from_name
}


def get_facility(**facility_field) -> dict:
    """Get facility profile from one of `facility_id` or `facility_name`."""

    if len(facility_field) != 1 or list(facility_field.keys())[0] not in _FACILITY_GETTERS:
        raise KeyError(f'Named parameters can only be one of {list(_FACILITY_GETTERS.keys())}')

    for field, value in facility_field.items():
        records = _FACILITY_GETTERS[field](value)
        if records.empty:
            raise ValueError(f'No facility with {field}={value}')
        return dict(records.iloc[0])
