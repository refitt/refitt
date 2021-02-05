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

"""Source endpoints."""


# type annotations
from typing import Union

# internal libs
from ....database.model import Client, Source, SourceType
from ..app import application
from ..response import endpoint, ParameterInvalid, NotFound, PermissionDenied
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters

# external libs
from flask import request


info: dict = {
    'Description': 'Request sources',
    'Endpoints': {
        '/source/<id>': {},
        '/source/<id>/type': {},
        '/source/<id>/user': {},
        '/source/<id>/facility': {},
        '/source/type/<id>': {},
    }
}


def _get_source(id_or_name: str, user_id: int, client_level: int) -> Source:
    """Query for source."""
    try:
        source = Source.from_id(int(id_or_name))
    except ValueError:
        source = Source.from_name(id_or_name)
    if source.user_id and source.user_id != user_id and client_level != 0:
        raise PermissionDenied(f'Source is not public')
    else:
        return source


@application.route('/source/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_source(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Query for source data."""
    params = collect_parameters(request, optional=['join'], defaults={'join': False})
    source = _get_source(id_or_name, client.user_id, client.level)
    return {'source': source.to_json(join=params['join'])}


info['Endpoints']['/source/<id>']['GET'] = {
    'Description': 'Request source by ID or name',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for source (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Source does not exist'},
    }
}


@application.route('/source/<id_or_name>/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_type_of_source(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Get source type for specific source by ID or name."""
    disallow_parameters(request)
    source = _get_source(id_or_name, client.user_id, client.level)
    return {'source_type': source.type.to_json()}


info['Endpoints']['/source/<id>/type']['GET'] = {
    'Description': 'Request type of specified source by ID or name',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for source (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Source does not exist'},
    }
}


@application.route('/source/<id_or_name>/user', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_user_of_source(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Get user for specific source by ID or name."""
    disallow_parameters(request)
    source = _get_source(id_or_name, client.user_id, client.level)
    if source.user_id is None:
        raise NotFound(f'No user for source ({source.id})')
    else:
        return {'user': source.user.to_json()}


info['Endpoints']['/source/<id>/user']['GET'] = {
    'Description': 'Request user of specified source by ID or name',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for source (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source user data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Source does not exist'},
    }
}


@application.route('/source/<id_or_name>/facility', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_facility_of_source(client: Client, id_or_name: str) -> dict:  # noqa: unused client
    """Get facility for specific source by ID or name."""
    disallow_parameters(request)
    source = _get_source(id_or_name, client.user_id, client.level)
    if source.facility_id is None:
        raise NotFound(f'No facility for source ({source.id})')
    else:
        return {'facility': source.facility.to_json()}


info['Endpoints']['/source/<id>/facility']['GET'] = {
    'Description': 'Request facility of specified source by ID or name',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for source (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source facility data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Source does not exist'},
    }
}


@application.route('/source/type/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_source_type(client: Client, id_or_name: Union[int, str]) -> dict:  # noqa: unused client
    """Get for source type by ID or name."""
    disallow_parameters(request)
    try:
        id = int(id_or_name)
        return {'source_type': SourceType.from_id(id).to_json()}
    except ValueError:
        name = str(id_or_name)
        return {'source_type': SourceType.from_name(name).to_json()}


info['Endpoints']['/source/type/<id>']['GET'] = {
    'Description': 'Request source type by ID or name',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for source type (or name)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Source type does not exist'},
    }
}
