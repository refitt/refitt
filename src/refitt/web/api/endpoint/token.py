# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Token creation endpoints."""


# internal libs
from ....database.model import Client, Session
from ..app import application
from ..response import endpoint
from ..auth import authenticate, authenticated, authorization

# public interface
__all__ = []


info: dict = {
    'Description': 'Requests for session token',
    'Endpoints': {
        '/token': {},
        '/token/<user_id>': {}
    }
}


@application.route('/token', methods=['GET'])
@endpoint('application/json')
@authenticate
def get_token(client: Client) -> dict:
    return {'token': Session.new(client.user_id).encrypt()}


info['Endpoints']['/token']['GET'] = {
    'Description': 'Request new token',
    'Permissions': 'User',
    'Requires': {
        'Auth': 'Basic HTTP authentication with key:secret',
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New token',
                'Type': 'application/json'
            },
        },
        403: {'Description': 'Authentication not found, invalid, or not permitted'},
    }
}


@application.route('/token/<int:user_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_token_for_user(admin: Client, user_id: int) -> dict:  # noqa: client not used
    try:
        return {'token': Session.new(user_id).encrypt()}
    except Client.NotFound:
        Client.new(user_id)
        return {'token': Session.new(user_id).encrypt()}


info['Endpoints']['/token/<user_id>']['GET'] = {
    'Description': 'Request new token on behalf of user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        }
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New token',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}
