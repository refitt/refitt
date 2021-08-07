# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Epoch endpoints."""


# external libs
from flask import request

# internal libs
from ....database.model import Client, Epoch
from ..app import application
from ..response import endpoint, ParameterInvalid, PayloadTooLarge
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters

# public interface
__all__ = ['info', ]


info: dict = {
    'Description': 'Request epochs',
    'Endpoints': {
        '/epoch': {},
        '/epoch/<id>': {},
    }
}


@application.route('/epoch', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_epoch(client: Client) -> dict:  # noqa: unused client
    """Query for epochs."""
    params = collect_parameters(request, required=['limit', ], optional=['offset', ])
    for name, value in params.items():
        if not isinstance(value, int):
            raise ParameterInvalid(f'Expected integer for parameter: {name}')
    if params['limit'] > 100:
        raise PayloadTooLarge('Must provide \'limit\' less than 100')
    return {'epoch': [epoch.to_json() for epoch in Epoch.select(**params)]}


info['Endpoints']['/epoch']['GET'] = {
    'Description': 'Request epochs (most recent first order)',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Parameters': {
            'limit': {
                'Description': 'Limit on number of returned epochs',
                'Type': 'Integer'
            }
        }
    },
    'Optional': {
        'Parameters': {
            'offset': {
                'Description': 'Filter epochs with ID greater than '
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Epoch data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/epoch/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_epoch_by_id(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for epoch by unique `id`."""
    disallow_parameters(request)
    return {'epoch': Epoch.from_id(id).to_json()}


info['Endpoints']['/epoch/<id>']['GET'] = {
    'Description': 'Request epoch by id',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for epoch',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Epoch data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Epoch not found'}
    }
}
