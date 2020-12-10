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

"""User profile endpoints."""


# type annotations
from typing import Union

# standard libs
import json

# internal libs
from ....database.model import Client, User, IntegrityError, NotFound
from ..app import application
from ..response import endpoint, PayloadNotFound, PayloadMalformed, PayloadInvalid, ConstraintViolation
from ..auth import authenticated, authorization

# external libs
from flask import request


@application.route('/user/<id_or_alias>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_user(admin: Client, id_or_alias: Union[int, str]) -> dict:  # noqa: unused client
    """Query for existing user profile."""
    try:
        user_id = int(id_or_alias)
        return {'user': User.from_id(user_id).to_json()}
    except ValueError:
        user_alias = str(id_or_alias)
        return {'user': User.from_alias(user_alias).to_json()}


@application.route('/user', methods=['POST'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_user(admin: Client) -> dict:  # noqa: unused client
    """Add new user profile."""
    payload = request.data
    if not payload:
        raise PayloadNotFound('Missing JSON data')
    try:
        profile = json.loads(payload.decode())
    except json.JSONDecodeError as error:
        raise PayloadMalformed('Invalid JSON data') from error
    try:
        User(**profile)
    except TypeError as error:
        raise PayloadInvalid('Invalid parameters in JSON data') from error
    try:
        user_id = profile.pop('id', None)
        if not user_id:
            user_id = User.add(profile)
        else:
            User.update(user_id, **profile)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': {'id': user_id}}


@application.route('/user/<int:user_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def update_user(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Update user profile attributes."""
    try:
        User.update(user_id, **request.args)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': {'id': user_id}}


@application.route('/user/<int:user_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_user(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Delete a user profile (assuming no existing relationships)."""
    try:
        User.delete(user_id)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': {'id': user_id}}


@application.route('/user/<int:user_id>/facility', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_all_user_facilities(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Query for facilities related to the given user."""
    return {
        'facility': [
            facility.to_json()
            for facility in User.from_id(user_id).facilities()
        ]
    }


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_user_facility(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Query for a facility related to the given user."""
    facilities = [facility.to_json() for facility in User.from_id(user_id).facilities()
                  if facility.id == facility_id]
    if not facilities:
        raise NotFound(f'Facility ({facility_id}) not associated with user ({user_id})')
    else:
        return {'facility': facilities[0]}


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_user_facility_association(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Associate the user with the given facility."""
    User.from_id(user_id).add_facility(facility_id)
    return {}


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_user_facility_association(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Query for facilities related to the given user."""
    User.from_id(user_id).delete_facility(facility_id)
    return {}
