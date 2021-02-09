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

"""Recommendation endpoints."""


# type annotations
from typing import Dict, Tuple, Callable

# external libs
from flask import request

# internal libs
from ....database.model import Client, Recommendation, RecommendationGroup, Base
from ..app import application
from ..response import endpoint, PermissionDenied, ParameterNotFound, ParameterInvalid, PayloadTooLarge, NotFound
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request recommendations',
    'Endpoints': {

        '/recommendation': {},
        '/recommendation/<id>': {},

        '/recommendation/<id>/group': {},
        '/recommendation/<id>/tag': {},
        '/recommendation/<id>/user': {},
        '/recommendation/<id>/facility': {},
        '/recommendation/<id>/object': {},
        '/recommendation/<id>/object/type': {},
        '/recommendation/<id>/forecast': {},

        '/recommendation/<id>/predicted': {},
        '/recommendation/<id>/predicted/type': {},
        '/recommendation/<id>/predicted/object': {},
        '/recommendation/<id>/predicted/object/type': {},
        '/recommendation/<id>/predicted/source': {},
        '/recommendation/<id>/predicted/source/type': {},
        '/recommendation/<id>/predicted/source/user': {},
        '/recommendation/<id>/predicted/forecast': {},

        '/recommendation/<id>/observed': {},
        '/recommendation/<id>/observed/type': {},
        '/recommendation/<id>/observed/object': {},
        '/recommendation/<id>/observed/object/type': {},
        '/recommendation/<id>/observed/source': {},
        '/recommendation/<id>/observed/source/type': {},
        '/recommendation/<id>/observed/source/user': {},
        '/recommendation/<id>/observed/source/facility': {},
        '/recommendation/<id>/observed/file': {},             # TODO: GET, PUT
        '/recommendation/<id>/observed/file/type': {},        # TODO: GET

        '/recommendation/history': {},

        '/recommendation/group': {},
        '/recommendation/group/<id>': {},
    }
}


def is_owner(recommendation: Recommendation, client: Client) -> bool:
    """Permission denied for recommendations that do not belong to you."""
    return recommendation.user_id == client.user_id or client.level <= 1


def get(id: int, client: Client) -> Recommendation:
    """Fetch recommendation by `id`."""
    recommendation = Recommendation.from_id(id)
    if is_owner(recommendation, client):
        return recommendation
    else:
        raise PermissionDenied('Recommendation is not public')


recommendation_slices: Dict[str, Tuple[str, Callable[[Recommendation], Base]]] = {

    'group':                     ('recommendation_group', lambda r: r.group),
    'tag':                       ('recommendation_tag',   lambda r: r.tag),
    'user':                      ('user',                 lambda r: r.user),
    'facility':                  ('facility',             lambda r: r.facility),
    'object':                    ('object',               lambda r: r.object),
    'object/type':               ('object_type',          lambda r: r.object.type),
    'forecast':                  ('forecast',             lambda r: r.forecast),

    'predicted/type':            ('observation_type',     lambda r: r.predicted.type),
    'predicted/object':          ('object',               lambda r: r.predicted.object),
    'predicted/object/type':     ('object_type',          lambda r: r.predicted.object.type),
    'predicted/source':          ('source',               lambda r: r.predicted.source),
    'predicted/source/type':     ('source_type',          lambda r: r.predicted.source.type),
    'predicted/source/user':     ('user',                 lambda r: r.predicted.source.user),

    'observed/type':             ('observation_type',     lambda r: r.observed.type),
    'observed/object':           ('object',               lambda r: r.observed.object),
    'observed/object/type':      ('object_type',          lambda r: r.observed.object.type),
    'observed/source':           ('source',               lambda r: r.observed.source),
    'observed/source/type':      ('source_type',          lambda r: r.observed.source.type),
    'observed/source/user':      ('user',                 lambda r: r.observed.source.user),
    'observed/source/facility':  ('facility',             lambda r: r.observed.source.facility),
}


@application.route('/recommendation', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_next(client: Client) -> dict:
    """Query for recommendations for user."""
    optional = ['group_id', 'facility_id', 'limiting_magnitude', 'limit', 'join']
    params = collect_parameters(request, optional=optional, defaults={'join': False})
    join = params.pop('join')
    return {'recommendation': [recommendation.to_json(join=join)
                               for recommendation in Recommendation.next(user_id=client.user_id, **params)]}


info['Endpoints']['/recommendation']['GET'] = {
    'Description': 'Request next recommendations for user',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Optional': {
        'Parameters': {
            'group_id': {
                'Description': 'Unique ID for recommendation group (defaults to latest)',
                'Type': 'Integer'
            },
            'facility_id': {
                'Description': 'Unique ID for facility (filters out other facilities)',
                'Type': 'Integer'
            },
            'limiting_magnitude': {
                'Description': 'Specify an upper magnitude brightness limit',
                'Type': 'Float'
            },
            'limit': {
                'Description': 'Limit on number of returned observations (default: none)',
                'Type': 'Integer'
            },
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation set',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/recommendation/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_by_id(client: Client, id: int) -> dict:
    """Query for recommendation by unique `id`."""
    params = collect_parameters(request, optional=['join', ], defaults={'join': False})
    return {'recommendation': get(id, client).to_json(**params)}


info['Endpoints']['/recommendation/<id>']['GET'] = {
    'Description': 'Request recommendation by id',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Optional': {
        'Parameters': {
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation not found'}
    }
}


@application.route('/recommendation/<int:id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def put_recommendation_attribute(client: Client, id: int) -> dict:  # noqa: unused client
    """Alter recommendation attribute by unique `id`."""
    get(id, client)  # check that client is owner of recommendation
    optional = ['accepted', 'rejected']
    params = collect_parameters(request, optional=optional)
    if params:
        Recommendation.update(id, **params)
        return {}
    else:
        raise ParameterNotFound(f'Expected one of {optional}')


info['Endpoints']['/recommendation/<id>']['PUT'] = {
    'Description': 'Alter recommendation by id',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Optional': {
        'Parameters': {
            'accepted': {
                'Description': 'Set accepted as true/false',
                'Type': 'Boolean'
            },
            'rejected': {
                'Description': 'Set rejected as true/false',
                'Type': 'Boolean'
            },
        },
    },
    'Responses': {
        200: {'Description': 'Success'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation not found'},
    }
}


@application.route('/recommendation/<int:id>/<path:relation>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_partial(client: Client, id: int, relation: str) -> dict:
    """Query for recommendation member relationship by unique `id` and `relation` path."""
    try:
        name, get_member = recommendation_slices[relation]
    except KeyError:
        raise NotFound(f'/recommendation/{id}/{relation}')
    params = collect_parameters(request, optional=['join', ], defaults={'join': False})
    return {name: get_member(get(id, client)).to_json(**params)}


for path in recommendation_slices:
    phrase = path.replace('/', ' ')
    info['Endpoints'][f'/recommendation/<id>/{path}']['GET'] = {
        'Description': f'Request {phrase} for recommendation by ID',
        'Permissions': 'Owner',
        'Requires': {
            'Auth': 'Authorization Bearer Token',
        },
        'Optional': {
            'Parameters': {
                'join': {
                    'Description': 'Include related data',
                    'Type': 'Boolean'
                },
            },
        },
        'Responses': {
            200: {
                'Description': 'Success',
                'Payload': {
                    'Description': f'Recommendation {phrase} data',
                    'Type': 'application/json'
                },
            },
            401: {'Description': 'Access revoked, token expired, or unauthorized'},
            403: {'Description': 'Token not found or invalid'},
            404: {'Description': f'Recommendation or {phrase} not found'}
        }
    }


@application.route('/recommendation/group', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_group(client: Client) -> dict:  # noqa: unused client
    """Query for recommendation groups."""
    params = collect_parameters(request, required=['limit', ], optional=['offset', ])
    for name, value in params.items():
        if not isinstance(value, int):
            raise ParameterInvalid(f'Expected integer for parameter: {name}')
    if params['limit'] > 100:
        raise PayloadTooLarge('Must provide \'limit\' less than 100')
    return {'recommendation_group': [group.to_json() for group in RecommendationGroup.select(**params)]}


info['Endpoints']['/recommendation/group']['GET'] = {
    'Description': 'Request recommendation groups (most recent first order)',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Parameters': {
            'limit': {
                'Description': 'Limit on number of returned groups',
                'Type': 'Integer'
            }
        }
    },
    'Optional': {
        'Parameters': {
            'offset': {
                'Description': 'Filter groups with ID greater than '
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation group set',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation group not found'}
    }
}


@application.route('/recommendation/group/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_group_by_id(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for recommendation group by unique `id`."""
    disallow_parameters(request)
    return {'recommendation_group': RecommendationGroup.from_id(id).to_json()}


info['Endpoints']['/recommendation/group/<id>']['GET'] = {
    'Description': 'Request recommendation group by id',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation group data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation group not found'}
    }
}


@application.route('/recommendation/history', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_history(client: Client) -> dict:
    """Query for recommendation history by group ID."""
    params = collect_parameters(request, required=['group_id'])
    if not isinstance(params['group_id'], int):
        raise ParameterInvalid(f'Expected integer for parameter: group_id')
    return {'recommendation': [
        recommendation.to_json()
        for recommendation in Recommendation.history(user_id=client.user_id, group_id=params['group_id'])
    ]}


info['Endpoints']['/recommendation/group/<id>']['GET'] = {
    'Description': 'Request recommendation group by id',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation group data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation group not found'}
    }
}
