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


# internal libs
from ....database.model import Client, Object, ObjectType
from ....database.core import Session
from ..app import application
from ..response import endpoint, ParameterInvalid
from ..auth import authenticated, authorization

# external libs
from flask import request


info: dict = {
    'Description': 'Request objects',
    'Endpoints': {
        '/object/<id>': {},
        '/object/<id>/type': {},
        '/object/type': {},
        '/object/type/<id>': {},
    }
}


@application.route('/object/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object(client: Client, id_or_name: str) -> dict:  # noqa: unused client
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


info['Endpoints']['/object/<id>']['GET'] = {
    'Description': 'Request object by ID or name',
    'Permissions': 'Anyone',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Object data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Object does not exist'},
    }
}


@application.route('/object/<id_or_name>/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_type_from_object(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Get object type for specific object by ID or name."""
    try:
        object_id = int(id_or_name)
        return {'object_type': Object.from_id(object_id).type.to_json()}
    except ValueError:
        object_name = str(id_or_name)
        return {'object_type': Object.from_name(object_name).type.to_json()}


info['Endpoints']['/object/<id>/type']['GET'] = {
    'Description': 'Request type of specified object by ID or name',
    'Permissions': 'Anyone',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Object type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Object does not exist'},
    }
}


@application.route('/object/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object_types(client: Client) -> dict:  # noqa: unused client
    """Get list of all object types."""
    session = Session()
    object_types = session.query(ObjectType).all()
    return {'object_type': [object_type.to_json() for object_type in object_types]}


info['Endpoints']['/object/type']['GET'] = {
    'Description': 'Request all object types',
    'Permissions': 'Anyone',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'List of object type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/object/type/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object_type(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Get for object type by ID or name."""
    try:
        id = int(id_or_name)
        return {'object_type': ObjectType.from_id(id).to_json()}
    except ValueError:
        name = str(id_or_name)
        return {'object_type': ObjectType.from_name(name).to_json()}


info['Endpoints']['/object/type/<id>']['GET'] = {
    'Description': 'Request object type by ID or name',
    'Permissions': 'Anyone',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object type (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Object type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Object type does not exist'},
    }
}
