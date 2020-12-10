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

"""Object endpoints."""


# type annotations
from typing import Union

# internal libs
from ....database.model import Client, Object, ObjectType
from ....database.core import Session
from ..app import application
from ..response import endpoint, ParameterInvalid
from ..auth import authenticated, authorization

# external libs
from flask import request


@application.route('/object/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object(client: Client, id_or_name: Union[int, str]) -> dict:  # noqa: unused client
    """Query for object data."""
    params = dict(request.args)
    join = params.pop('join', 'true')
    if join not in ('1', '0', 'true', 'false'):
        raise ParameterInvalid('Parameter \'join\' should be true/false')
    else:
        join = True if join in ('1', 'true') else False
    for key, value in params.items():
        raise ParameterInvalid(f'Parameter not supported: \'{key}\'')
    try:
        object_id = int(id_or_name)
        return {'object': Object.from_id(object_id).to_json(join=join)}
    except ValueError:
        object_name = str(id_or_name)
        return {'object': Object.from_name(object_name).to_json(join=join)}


@application.route('/object/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object_types(client: Client) -> dict:  # noqa: unused client
    """Query for object type data."""
    session = Session()
    object_types = session.query(ObjectType).all()
    return {'object_type': [object_type.to_json() for object_type in object_types]}


@application.route('/object/type/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object_type(client: Client, id_or_name: Union[int, str]) -> dict:  # noqa: unused client
    """Query for object type data."""
    try:
        object_type_id = int(id_or_name)
        return {'object_type': ObjectType.from_id(object_type_id).to_json()}
    except ValueError:
        object_type_name = str(id_or_name)
        return {'object_type': ObjectType.from_name(object_type_name).to_json()}
