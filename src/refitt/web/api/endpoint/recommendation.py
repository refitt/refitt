# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Recommendation endpoints."""


# type annotations
from typing import Dict, Tuple, Callable, IO

# standard libs
from io import BytesIO
from datetime import datetime

# external libs
from flask import request

# internal libs
from refitt.database.model import (Client, Recommendation, File, FileType, Observation,
                                   Source, ModelInterface, Epoch, Model)
from refitt.web.api.app import application
from refitt.web.api.auth import authenticated, authorization
from refitt.web.api.tools import collect_parameters, disallow_parameters, require_file, require_data
from refitt.web.api.response import (endpoint, PermissionDenied, ParameterNotFound, ParameterInvalid,
                                     PayloadMalformed, NotFound)

# public interface
__all__ = ['info', 'recommendation_slices', 'FILE_SIZE_LIMIT', ]


info: dict = {
    'Description': 'Request recommendations',
    'Endpoints': {
        '/recommendation': {},
        '/recommendation/<id>': {},
        '/recommendation/<id>/epoch': {},
        '/recommendation/<id>/tag': {},
        '/recommendation/<id>/user': {},
        '/recommendation/<id>/facility': {},
        '/recommendation/<id>/object': {},
        '/recommendation/<id>/object/type': {},
        '/recommendation/<id>/predicted': {},
        '/recommendation/<id>/predicted/type': {},
        '/recommendation/<id>/predicted/object': {},
        '/recommendation/<id>/predicted/object/type': {},
        '/recommendation/<id>/predicted/source': {},
        '/recommendation/<id>/predicted/source/type': {},
        '/recommendation/<id>/predicted/source/user': {},
        '/recommendation/<id>/observed': {},
        '/recommendation/<id>/observed/type': {},
        '/recommendation/<id>/observed/object': {},
        '/recommendation/<id>/observed/object/type': {},
        '/recommendation/<id>/observed/source': {},
        '/recommendation/<id>/observed/source/type': {},
        '/recommendation/<id>/observed/source/user': {},
        '/recommendation/<id>/observed/source/facility': {},
        '/recommendation/<id>/observed/file': {},
        '/recommendation/<id>/observed/file/type': {},
        '/recommendation/<id>/model': {},
        '/recommendation/<id>/model/<type_id>': {},
        '/recommendation/history': {},
        '/recommendation/total': {},
    }
}


def is_owner(recommendation: Recommendation, client: Client) -> bool:
    """Permission denied for recommendations that do not belong to you (and not admin)."""
    # TODO: is this right?
    return recommendation.user_id == client.user_id or client.level <= 1


def get(id: int, client: Client) -> Recommendation:
    """Fetch recommendation by `id`."""
    recommendation = Recommendation.from_id(id)
    if is_owner(recommendation, client):
        return recommendation
    else:
        raise PermissionDenied('Recommendation is not public')


recommendation_slices: Dict[str, Tuple[str, Callable[[Recommendation], ModelInterface]]] = {
    'epoch':                     ('epoch',                lambda r: r.epoch),
    'tag':                       ('recommendation_tag',   lambda r: r.tag),
    'user':                      ('user',                 lambda r: r.user),
    'facility':                  ('facility',             lambda r: r.facility),
    'object':                    ('object',               lambda r: r.object),
    'object/type':               ('object_type',          lambda r: r.object.type),

    'predicted':                 ('observation',          lambda r: r.predicted),
    'predicted/type':            ('observation_type',     lambda r: r.predicted.type),
    'predicted/object':          ('object',               lambda r: r.predicted.object),
    'predicted/object/type':     ('object_type',          lambda r: r.predicted.object.type),
    'predicted/source':          ('source',               lambda r: r.predicted.source),
    'predicted/source/type':     ('source_type',          lambda r: r.predicted.source.type),
    'predicted/source/user':     ('user',                 lambda r: r.predicted.source.user),

    'observed':                  ('observation',          lambda r: r.observed),
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
    optional = ['epoch_id', 'facility_id', 'limiting_magnitude', 'limit', 'mode', 'join']
    params = collect_parameters(request, optional=optional, defaults={'join': False, 'mode': 'normal'})
    join = params.pop('join')
    mode = params.pop('mode')
    if mode not in Recommendation.QUERY_MODES:
        raise ParameterInvalid(f'Invalid recommendation mode: {mode}')
    if 'limiting_magnitude' in params and not isinstance(params['limiting_magnitude'], float):
        raise ParameterInvalid(f'Expected decimal number for \'limiting_magnitude\' '
                               f'(given {params["limiting_magnitude"]})')
    for opt in 'epoch_id', 'facility_id', 'limit':
        if opt in params and not isinstance(params[opt], int):
            raise ParameterInvalid(f'Expected integer for {opt} (given {params[opt]})')
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
            'epoch_id': {
                'Description': 'Unique ID for epoch (defaults to latest)',
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
                'Description': 'Limit on number of returned recommendations (default: none)',
                'Type': 'Integer'
            },
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            },
            'mode': {
                'Description': 'Mode to filter/sort recommendations by',
                'Type': 'String',
                'Choices': Recommendation.QUERY_MODES,
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
        400: {'Description': 'Parameter invalid'},
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
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
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
                'Description': 'Recommendation data',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
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
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
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
        400: {'Description': 'Parameter invalid'},
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
    member = get_member(get(id, client))
    if member is not None:
        if isinstance(member, list):
            return {name: [record.to_json(**params) for record in member]}
        else:
            return {name: member.to_json(**params)}
    else:
        raise NotFound(f'Member \'{relation}\' not available for recommendation ({id})')


for path in recommendation_slices:
    phrase = path.replace('/', ' ')
    info['Endpoints'][f'/recommendation/<id>/{path}']['GET'] = {
        'Description': f'Request {phrase} for recommendation by ID',
        'Permissions': 'Owner',
        'Requires': {
            'Auth': 'Authorization Bearer Token',
            'Path': {
                'id': {
                    'Description': 'Unique ID for recommendation',
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
                    'Description': f'Recommendation {phrase} data',
                    'Type': 'application/json'
                },
            },
            400: {'Description': 'Parameter invalid'},
            401: {'Description': 'Access revoked, token expired, or unauthorized'},
            403: {'Description': 'Token not found or invalid'},
            404: {'Description': f'Recommendation or {phrase} not found'}
        }
    }


@application.route('/recommendation/history', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_history(client: Client) -> dict:
    """Query for recommendation history by group ID."""
    params = collect_parameters(request, required=['epoch_id'])
    if not isinstance(params['epoch_id'], int):
        raise ParameterInvalid(f'Expected integer for parameter: epoch_id')
    return {'recommendation': [
        recommendation.to_json()
        for recommendation in Recommendation.history(user_id=client.user_id, epoch_id=params['epoch_id'])
    ]}


info['Endpoints']['/recommendation/history']['GET'] = {
    'Description': 'Request recommendation history',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Parameters': {
            'epoch_id': {
                'Description': 'The epoch ID',
                'Type': 'Integer'
            }
        }
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Recommendation set',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
    }
}


# limit on allowed file upload size
FILE_SIZE_LIMIT: int = 800 * 1024**2
# NOTE: 800M file allows single 10k-square CCD w/ 64-bit Integers
# Larger collections in size and number can be included if compressed


@application.route('/recommendation/<int:id>/observed/file', methods=['GET'])
@endpoint('application/octet-stream')
@authenticated
@authorization(level=None)
def get_recommendation_observed_file(client: Client, id: int) -> Tuple[IO, dict]:
    """Query for observation file by recommendation `id`."""
    recommendation = Recommendation.from_id(id)
    if recommendation.user_id != client.user_id and client.level > 1:
        raise PermissionDenied('Recommendation is not public')
    if recommendation.observation_id is None:
        raise NotFound('Missing observation record, cannot get file')
    disallow_parameters(request)
    file = File.from_observation(recommendation.observation_id)
    return BytesIO(file.data), {
        'as_attachment': True, 'download_name': file.name, 'conditional': False,
    }


info['Endpoints']['/recommendation/<id>/observed/file']['GET'] = {
    'Description': 'Request observation file by recommendation ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File attachment',
                'Type': 'application/octet-stream'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation, observation, or file does not exist'},
    }
}


@application.route('/recommendation/<int:id>/observed/file', methods=['POST'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def add_recommendation_observed_file(client: Client, id: int) -> dict:
    """Upload file associated with recommendation."""
    recommendation = Recommendation.from_id(id)
    if recommendation.user_id != client.user_id:
        raise PermissionDenied('Recommendation is not public')
    if recommendation.observation_id is None:
        raise NotFound('Missing observation record, cannot upload file')
    disallow_parameters(request)
    file_name, file_type, file_data = require_file(request, allowed_extensions=FileType.all_names(),
                                                   size_limit=FILE_SIZE_LIMIT)
    type_id = FileType.from_name(file_type).id
    try:
        file = File.from_observation(recommendation.observation_id)
        File.update(file.id, type_id=type_id, name=file_name, data=file_data)
    except File.NotFound:
        file = File.add({'observation_id': recommendation.observation_id, 'epoch_id': Epoch.latest().id,
                         'type_id': type_id, 'name': file_name, 'data': file_data})
    return {'file': {'id': file.id}}


info['Endpoints']['/recommendation/<id>/observed/file']['POST'] = {
    'Description': 'Upload file for observation associated with recommendation by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
        'Attachment': {
            'Description': 'File',
            'Type': 'application/octet-stream',
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New file ID',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'File attachment missing, malformed, or invalid'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation or observation not found'}
    }
}


@application.route('/recommendation/<int:id>/observed/file/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_observed_file_type(client: Client, id: int) -> dict:
    """Query for observation file type by recommendation `id`."""
    recommendation = Recommendation.from_id(id)
    if recommendation.user_id != client.user_id:
        raise PermissionDenied('Recommendation is not public')
    if recommendation.observation_id is None:
        raise NotFound('Missing observation record, cannot get file')
    disallow_parameters(request)
    file = File.from_observation(recommendation.observation_id)
    return {'file_type': file.type.to_json()}


info['Endpoints']['/recommendation/<id>/observed/file/type']['GET'] = {
    'Description': 'Request observation file type by recommendation ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation, observation, or file does not exist'},
    }
}


@application.route('/recommendation/<int:id>/observed', methods=['POST'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def add_recommendation_observed(client: Client, id: int) -> dict:
    """Upload new observation associated with recommendation by ID."""
    disallow_parameters(request)
    recommendation = Recommendation.from_id(id)
    if recommendation.user_id != client.user_id:
        raise PermissionDenied('Recommendation is not public')
    data = require_data(request, data_format='json', validate=Observation.from_dict,
                        required_fields=['type_id', 'value', 'error', 'time'])
    known_fields = {
        'object_id': recommendation.object_id,
        'source_id': Source.get_or_create(recommendation.user_id, recommendation.facility_id).id
    }
    try:
        time = datetime.fromisoformat(data.pop('time'))
    except ValueError as error:
        raise PayloadMalformed(str(error)) from error
    if recommendation.observation_id is None:
        observation = Observation.add({**known_fields, 'epoch_id': Epoch.latest().id, 'time': time, **data})
        Recommendation.update(recommendation.id, observation_id=observation.id)
        return {'observation': observation.to_json()}
    else:
        Observation.update(recommendation.observation_id,
                           **{'time': time, 'recorded': datetime.now().astimezone(), **data})
        return {'observation': recommendation.observed.to_json()}


info['Endpoints']['/recommendation/<id>/observed']['POST'] = {
    'Description': 'Upload observation associated with recommendation by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
        'Payload': {
            'Description': 'Observation data',
            'Type': 'application/json',
            'Fields': {
                'type_id': {
                    'Description': 'Observation type ID',
                    'Type': 'Integer'
                },
                'value': {
                    'Description': 'Observed magnitude (can be null)',
                    'Type': 'Float'
                },
                'error': {
                    'Description': 'Uncertainty in magnitude (can be null)',
                    'Type': 'Float'
                },
                'time': {
                    'Description': 'Precise time of observation (yyyy-mm-dd HH:MM:SS-ZZZZ)',
                    'Type': 'String'
                }
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New observation with ID',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Payload missing, malformed, or invalid'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation not found'}
    }
}


@application.route('/recommendation/<int:id>/model', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_model_info(client: Client, id: int) -> dict:
    """Query for model info by recommendation ID."""
    disallow_parameters(request)
    return {'model': [model.to_json() for model in get(id, client).model_info]}


info['Endpoints']['/recommendation/<id>/model']['GET'] = {
    'Description': f'Request model info for recommendation by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': f'Model info for recommendation',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Recommendation not found'}
    }
}


@application.route('/recommendation/<int:id>/model/<int:type_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_recommendation_model_by_type(client: Client, id: int, type_id: int) -> dict:
    """Query for model data by recommendation ID and model type ID."""
    disallow_parameters(request)
    models = [model for model in get(id, client).model_info if model.type_id == type_id]
    if not models:
        raise NotFound(f'No model with type_id={type_id} for recommendation with id={id}')
    return {'model': Model.from_id(models[0].id).to_json()}


info['Endpoints']['/recommendation/<id>/model/<type_id>']['GET'] = {
    'Description': 'Request model data for recommendation by ID and model type ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for recommendation',
                'Type': 'Integer',
            },
            'type_id': {
                'Description': 'Unique ID for model type',
                'Type': 'Integer',
            }
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
        404: {'Description': 'Recommendation or model not found'}
    }
}


@application.route('/recommendation/total', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=1)
def get_recommendation_totals(admin_client: Client, ) -> dict:  # noqa: unused client
    """Query for recommendation statistics."""
    params = collect_parameters(request, optional=['epoch_id', 'user_id', 'facility_id',
                                                   'accepted', 'rejected', 'fulfilled'])
    for opt in 'accepted', 'rejected', 'fulfilled':
        if opt in params and not isinstance(params[opt], bool):
            raise ParameterInvalid(f'Expected true/false for {opt} (given {params[opt]})')
    for opt in 'epoch_id', 'user_id', 'facility_id':
        if opt in params and not isinstance(params[opt], int):
            raise ParameterInvalid(f'Expected integer for {opt} (given {params[opt]})')
    query = Recommendation.query()
    fulfilled = params.pop('fulfilled', False)
    if fulfilled:
        query = query.filter(Recommendation.observation_id.isnot(None))
    for opt, value in params.items():
        query = query.filter_by(**{opt: value})
    return {
        'count': query.count(),
    }


info['Endpoints']['/recommendation/total']['GET'] = {
    'Description': 'Get recommendation statistics',
    'Permissions': 'Admin',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Optional': {
        'Parameters': {
            'epoch_id': {
                'Description': 'Unique ID for epoch (defaults to any epoch)',
                'Type': 'Integer'
            },
            'user_id': {
                'Description': 'Unique ID for user (filters out other users)',
                'Type': 'Integer'
            },
            'facility_id': {
                'Description': 'Unique ID for facility (filters out other facilities)',
                'Type': 'Integer'
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Count of recommendations',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'Parameter invalid'},
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
    }
}
