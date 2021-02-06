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
from typing import Dict, Tuple, Callable, Union

# external libs
from flask import request

# internal libs
from ....database.model import Client, Recommendation, RecommendationGroup, Observation, Base
from ..app import application
from ..response import endpoint, PermissionDenied
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request recommendations',
    'Endpoints': {

        '/recommendation': {},
        '/recommendation/<id>': {},                           # TODO: GET, PUT

        '/recommendation/<id>/group': {},                     # TODO: GET
        '/recommendation/<id>/tag': {},                       # TODO: GET
        '/recommendation/<id>/user': {},                      # TODO: GET
        '/recommendation/<id>/facility': {},                  # TODO: GET
        '/recommendation/<id>/object': {},                    # TODO: GET
        '/recommendation/<id>/object/type': {},               # TODO: GET
        '/recommendation/<id>/forecast': {},                  # TODO: GET

        '/recommendation/<id>/predicted': {},                 # TODO: GET
        '/recommendation/<id>/predicted/type': {},            # TODO: GET
        '/recommendation/<id>/predicted/object': {},          # TODO: GET
        '/recommendation/<id>/predicted/object/type': {},     # TODO: GET
        '/recommendation/<id>/predicted/source': {},          # TODO: GET
        '/recommendation/<id>/predicted/source/type': {},     # TODO: GET
        '/recommendation/<id>/predicted/source/user': {},     # TODO: GET
        '/recommendation/<id>/predicted/forecast': {},        # TODO: GET

        '/recommendation/<id>/observed': {},                  # TODO: GET
        '/recommendation/<id>/observed/type': {},             # TODO: GET
        '/recommendation/<id>/observed/object': {},           # TODO: GET
        '/recommendation/<id>/observed/object/type': {},      # TODO: GET
        '/recommendation/<id>/observed/source': {},           # TODO: GET
        '/recommendation/<id>/observed/source/type': {},      # TODO: GET
        '/recommendation/<id>/observed/source/user': {},      # TODO: GET
        '/recommendation/<id>/observed/source/facility': {},  # TODO: GET
        '/recommendation/<id>/observed/file': {},             # TODO: GET
        '/recommendation/<id>/observed/file/type': {},        # TODO: GET

        '/recommendation/group': {},                          # TODO: GET
        '/recommendation/group/<id>': {},                     # TODO: GET
    }
}


def is_owner(recommendation: Recommendation, client: Client) -> bool:
    """Permission denied for recommendations that do not belong to you."""
    return recommendation.user_id == client.user_id or client.level > 1


def get(id: int, client: Client) -> Recommendation:
    """Fetch recommendation by `id`."""
    recommendation = Recommendation.from_id(id)
    if is_owner(recommendation, client):
        return recommendation
    else:
        raise PermissionDenied('Recommendation is not public')


observation_slices: Dict[str, Tuple[str, Callable[[Observation], Base]]] = {
    'type':            ('observation_type',  lambda o: o.type),
    'object':          ('object',            lambda o: o.object),
    'object/type':     ('object_type',       lambda o: o.object.type),
    'source':          ('source',            lambda o: o.source),
    'source/type':     ('source_type',       lambda o: o.source.type),
    'source/user':     ('user',              lambda o: o.source.user),
    'source/facility': ('facility',          lambda o: o.source.facility),
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
