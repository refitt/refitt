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

"""REFITT's REST-API implementation."""

# type annotations
from __future__ import annotations

# standard libs
import json

# external libs
from flask import Flask, Response, request

# internal libs
from ...database.auth import Client
from .response import STATUS, restful
from .auth import authenticate, authenticated, authorization
from .endpoints import token, profile
from .logging import logged

# flask application
application = Flask(__name__)


@application.errorhandler(STATUS['Not Found'])
def not_found(error=None) -> Response:
    """Response to an invalid request."""
    return Response(json.dumps({'status': 'error',
                                'message': f'not found: {request.path}'}),
                    status=STATUS['Not Found'],
                    mimetype='application/json')


@application.route('/token', methods=['GET'])
@logged
@restful
@authenticate
def get_token(client: Client) -> dict:
    return {'access': token.get(client.client_id)}


@application.route('/token/<int:user_id>', methods=['GET'])
@logged
@restful
@authenticated
@authorization(level=0)
def get_user_token(client: Client, user_id: int) -> dict:
    return {'access': token.get_user(user_id)}


@application.route('/profile/user', methods=['POST'])
@logged
@restful
@authenticated
@authorization(level=0)
def post_user_profile(client: Client) -> dict:
    return {'profile': profile.user.post(request.json)}


@application.route('/profile/user/<int:user_id>', methods=['GET'])
@logged
@restful
@authenticated
@authorization(level=0)
def get_user_profile(client: Client, user_id: int) -> dict:
    return {'profile': profile.user.get(user_id)}


@application.route('/profile/user/<int:user_id>', methods=['PUT'])
@logged
@restful
@authenticated
@authorization(level=0)
def put_user_profile(client: Client, user_id: int) -> dict:
    return {'profile': profile.user.put(user_id, request.json)}


@application.route('/profile/user/<int:user_id>', methods=['DELETE'])
@logged
@restful
@authenticated
@authorization(level=0)
def delete_user_profile(client: Client, user_id: int) -> dict:
    return {'profile': profile.user.delete(user_id)}


@application.route('/profile/facility', methods=['POST'])
@logged
@restful
@authenticated
@authorization(level=0)
def post_facility_profile(client: Client) -> dict:
    return {'profile': profile.facility.post(request.json)}


@application.route('/profile/facility/<int:facility_id>', methods=['GET'])
@logged
@restful
@authenticated
@authorization(level=0)
def get_facility_profile(client: Client, facility_id: int) -> dict:
    return {'profile': profile.facility.get(facility_id)}


@application.route('/profile/facility/<int:facility_id>', methods=['PUT'])
@logged
@restful
@authenticated
@authorization(level=0)
def put_facility_profile(client: Client, facility_id: int) -> dict:
    return {'profile': profile.facility.put(facility_id, request.json)}


@application.route('/profile/facility/<int:facility_id>', methods=['DELETE'])
@logged
@restful
@authenticated
@authorization(level=0)
def delete_facility_profile(client: Client, facility_id: int) -> dict:
    return {'profile': profile.facility.delete(facility_id)}


@application.route('/recommendation', methods=['GET'])
@logged
@restful
@authenticated
@authorization(level=None)
def get_recommendation(client: Client) -> dict:
    raise NotImplementedError(request.path)


@application.route('/recommendation/<int:recommendation_id>', methods=['GET'])
@logged
@restful
@authenticated
@authorization(level=None)
def get_single_recommendation(client: Client, recommendation_id) -> dict:
    raise NotImplementedError(request.path)


@application.route('/recommendation/<int:recommendation_id>', methods=['POST'])
@logged
@restful
@authenticated
@authorization(level=None)
def post_recommendation(client: Client, recommendation_id) -> dict:
    raise NotImplementedError(request.path)


@application.route('/recommendation/<int:recommendation_id>/<string:action>', methods=['PUT'])
@logged
@restful
@authenticated
@authorization(level=None)
def put_recommendation(client: Client, recommendation_id, action) -> dict:
    raise NotImplementedError(request.path)
