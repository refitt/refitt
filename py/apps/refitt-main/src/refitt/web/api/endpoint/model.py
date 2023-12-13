# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Model endpoints."""


# external libs
from flask import request
from sqlalchemy.orm import joinedload

# internal libs
from refitt.database.model import Client, Recommendation, Model, Observation
from refitt.web.api.app import application
from refitt.web.api.auth import authenticated, authorization
from refitt.web.api.tools import collect_parameters, disallow_parameters
from refitt.web.api.response import endpoint, PermissionDenied, ParameterInvalid, PayloadTooLarge

# public interface
__all__ = ['info', ]


info: dict = {
    'Description': 'Request model data',
    'Endpoints': {
        '/model': {},
        '/model/<id>': {},
        '/model/<id>/type': {},  # TODO: GET
        '/model/<id>/epoch': {},  # TODO: GET
        '/model/<id>/object': {},  # TODO: GET
        '/model/<id>/observation': {},  # TODO: GET
        '/model/<id>/observation/type': {},  # TODO: GET
        '/model/type': {},  # TODO: GET
        '/model/type/<id>': {},  # TODO: GET
    }
}


def count_if(user_id: int, observation_id: int) -> int:
    """Count of recommendations for given user for given prediction."""
    return Recommendation.query().filter_by(user_id=user_id, predicted_observation_id=observation_id).count()


def is_associated(model: Model, client: Client) -> bool:
    """Permission denied on models for objects not recommended to user."""
    return client.level <= 1 or count_if(client.user_id, model.observation_id) > 0


def get(id: int, client: Client) -> Model:
    """Fetch model by `id`."""
    model = Model.from_id(id)
    if is_associated(model, client):
        return model
    else:
        raise PermissionDenied('Model is not public')


@application.route('/model', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=1)
def get_models(admin_client: Client) -> dict:  # noqa: unused client
    """Query for models."""
    params = collect_parameters(request,
                                optional=['epoch_id', 'object_id', 'type_id', 'limit', 'join', 'include_data'],
                                defaults={'join': False, 'include_data': False})
    for opt in 'epoch_id', 'type_id', 'object_id', 'limit':
        if opt in params and not isinstance(params[opt], int):
            raise ParameterInvalid(f'Expected integer for {opt} (given {request.args[opt]})')
        if opt in params and isinstance(params[opt], bool):
            raise ParameterInvalid(f'Expected integer for {opt} (given {request.args[opt]})')
    if 'limit' not in params and 'epoch_id' not in params and 'object_id' not in params:
        raise PayloadTooLarge(f'Cannot query models without \'epoch_id\' or \'object_id\' and without \'limit\'')
    if 'limit' not in params and params['include_data'] is True:
        raise PayloadTooLarge(f'Cannot include full model data without \'limit\'')
    join = params.pop('join')
    include_data = params.pop('include_data')
    type_id = params.pop('type_id', None)
    epoch_id = params.pop('epoch_id', None)
    object_id = params.pop('object_id', None)
    limit = params.pop('limit', None)
    query = Model.query()
    if object_id:
        query = query.join(Observation)
        query = query.filter(Observation.object_id == object_id)
    if type_id:
        query = query.filter(Model.type_id == type_id)
    if epoch_id:
        query = query.filter(Model.epoch_id == epoch_id)
    if limit:
        query = query.limit(limit)
    models = [model.to_json(join=join) for model in query.all()]
    if not include_data:
        for model in models:
            model.pop('data')
    return {'model': models}


info['Endpoints']['/model']['GET'] = {
    'Description': 'Query for models',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Optional': {
        'Parameters': {
            'epoch_id': {
                'Description': 'Unique ID for epoch',
                'Type': 'Integer'
            },
            'type_id': {
                'Description': 'Unique ID for model type',
                'Type': 'Integer'
            },
            'object_id': {
                'Description': 'Unique ID for object',
                'Type': 'Integer'
            },
            'limit': {
                'Description': 'Limit on number of returned models (default: none)',
                'Type': 'Integer'
            },
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            },
            'include_data': {
                'Description': 'Include all data (not just metadata)',
                'Type': 'Boolean'
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Model set',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        413: {'Description': 'Too much data requested'},
    }
}


@application.route('/model/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_model_by_id(client: Client, id: int) -> dict:
    """Query for model by unique `id`."""
    params = collect_parameters(request, optional=['join', ], defaults={'join': False})
    return {'model': get(id, client).to_json(**params)}


info['Endpoints']['/model/<id>']['GET'] = {
    'Description': 'Request model by id',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for model',
                'Type': 'Integer',
            }
        },
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
                'Description': 'Model data',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Model not found'}
    }
}


# @application.route('/recommendation/<int:id>/<path:relation>', methods=['GET'])
# @endpoint('application/json')
# @authenticated
# @authorization(level=None)
# def get_recommendation_partial(client: Client, id: int, relation: str) -> dict:
#     """Query for recommendation member relationship by unique `id` and `relation` path."""
#     try:
#         name, get_member = recommendation_slices[relation]
#     except KeyError:
#         raise NotFound(f'/recommendation/{id}/{relation}')
#     params = collect_parameters(request, optional=['join', ], defaults={'join': False})
#     member = get_member(get(id, client))
#     if member is not None:
#         if isinstance(member, list):
#             return {name: [record.to_json(**params) for record in member]}
#         else:
#             return {name: member.to_json(**params)}
#     else:
#         raise NotFound(f'Member \'{relation}\' not available for recommendation ({id})')
#
#
# for path in recommendation_slices:
#     phrase = path.replace('/', ' ')
#     info['Endpoints'][f'/recommendation/<id>/{path}']['GET'] = {
#         'Description': f'Request {phrase} for recommendation by ID',
#         'Permissions': 'Owner',
#         'Requires': {
#             'Auth': 'Authorization Bearer Token',
#             'Path': {
#                 'id': {
#                     'Description': 'Unique ID for recommendation',
#                     'Type': 'Integer',
#                 }
#             },
#         },
#         'Optional': {
#             'Parameters': {
#                 'join': {
#                     'Description': 'Include related data',
#                     'Type': 'Boolean'
#                 },
#             },
#         },
#         'Responses': {
#             200: {
#                 'Description': 'Success',
#                 'Payload': {
#                     'Description': f'Recommendation {phrase} data',
#                     'Type': 'application/json'
#                 },
#             },
#             400: {'Description': 'Parameter invalid'},
#             401: {'Description': 'Access revoked, token expired, or unauthorized'},
#             403: {'Description': 'Token not found or invalid'},
#             404: {'Description': f'Recommendation or {phrase} not found'}
#         }
#     }
