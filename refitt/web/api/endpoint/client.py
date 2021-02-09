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

"""Client credential creation endpoints."""


# internal libs
from ....database.model import Client
from ..app import application
from ..response import endpoint
from ..auth import authenticated, authorization


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
