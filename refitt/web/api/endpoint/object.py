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


# external libs
from flask import request

# internal libs
from ....database.model import Client, Object, ObjectType
from ..app import application
from ..response import endpoint
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request objects',
    'Endpoints': {
        '/object/<id>': {},
        '/object/<id>/type': {},
        '/object/type/<id>': {},
    }
}


@application.route('/object/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for object data by `id`."""
    params = collect_parameters(request, optional=['join'], defaults={'join': False})
    return {'object': Object.from_id(id).to_json(**params)}


info['Endpoints']['/object/<id>']['GET'] = {
    'Description': 'Request object by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
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


@application.route('/object/<int:object_id>/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_type_from_object(client: Client, object_id: int) -> dict:  # noqa: unused client
    """Get object type for specific object by ID."""
    disallow_parameters(request)
    return {'object_type': Object.from_id(object_id).type.to_json()}


info['Endpoints']['/object/<id>/type']['GET'] = {
    'Description': 'Request type of specified object by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object',
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


@application.route('/object/type/<int:type_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_object_type(client: Client, type_id: int) -> dict:  # noqa: unused client
    """Get for object type by ID."""
    disallow_parameters(request)
    return {'object_type': ObjectType.from_id(type_id).to_json()}


info['Endpoints']['/object/type/<id>']['GET'] = {
    'Description': 'Request object type by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for object type',
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
