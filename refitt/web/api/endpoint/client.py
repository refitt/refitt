# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Client credential creation endpoints."""


# internal libs
from ....database.model import Client
from ..app import application
from ..response import endpoint
from ..auth import authenticated, authorization

# public interface
__all__ = []


info: dict = {
    'Description': 'Requests for client credential generation',
    'Endpoints': {
        '/client/<user_id>': {},
        '/client/secret/<user_id>': {}
    }
}


@application.route('/client/<int:user_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_client(admin: Client, user_id: int) -> dict:  # noqa: admin client not used
    try:
        key, secret = Client.new_key(user_id)
    except Client.NotFound:
        key, secret, client = Client.new(user_id)
    return {'client': {'key': key.value, 'secret': secret.value}}


info['Endpoints']['/client/<user_id>']['GET'] = {
    'Description': 'Generate new client key and secret on behalf of user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Client credentials',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}


@application.route('/client/secret/<int:user_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_client_secret(admin: Client, user_id: int) -> dict:  # noqa: admin client not used
    try:
        key, secret = Client.new_secret(user_id)
    except Client.NotFound:
        key, secret, client = Client.new(user_id)
    return {'client': {'key': key.value, 'secret': secret.value}}


info['Endpoints']['/client/secret/<user_id>']['GET'] = {
    'Description': 'Generate new client secret on behalf of user.',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Client credentials',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}
