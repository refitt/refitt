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


# internal libs
from .app import application
from .endpoint import token, client



# @application.route('/profile/user', methods=['POST'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def post_user_profile(client: Client) -> dict:
#     return {'profile': profile.user.post(request.json)}
#
#
# @application.route('/profile/user/<string:id_or_alias>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def get_user_profile(client: Client, id_or_alias: str) -> dict:
#     return {'profile': profile.user.get(id_or_alias)}
#
#
# @application.route('/profile/user/<string:id_or_alias>', methods=['PUT'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def put_user_profile(client: Client, id_or_alias: str) -> dict:
#     return {'profile': profile.user.put(id_or_alias, request.json)}
#
#
# @application.route('/profile/user/<string:id_or_alias>', methods=['DELETE'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def delete_user_profile(client: Client, id_or_alias: str) -> dict:
#     return {'profile': profile.user.delete(id_or_alias)}
#
#
# @application.route('/profile/facility', methods=['POST'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def post_facility_profile(client: Client) -> dict:
#     return {'profile': profile.facility.post(request.json)}
#
#
# @application.route('/profile/facility/<string:id_or_name>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def get_facility_profile(client: Client, id_or_name: str) -> dict:
#     return {'profile': profile.facility.get(id_or_name)}
#
#
# @application.route('/profile/facility/<string:id_or_name>', methods=['PUT'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def put_facility_profile(client: Client, id_or_name: str) -> dict:
#     return {'profile': profile.facility.put(id_or_name, request.json)}
#
#
# @application.route('/profile/facility/<string:id_or_name>', methods=['DELETE'])
# @endpoint
# @authenticated
# @authorization(level=0)
# def delete_facility_profile(client: Client, id_or_name: str) -> dict:
#     return {'profile': profile.facility.delete(id_or_name)}
#
#
# @application.route('/recommendation', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_recommendation(client: Client) -> dict:
#     return {'recommendation': recommendation.get(client.user_id, **request.args)}
#
#
# @application.route('/recommendation/<int:recommendation_id>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_single_recommendation(client: Client, recommendation_id: int) -> dict:
#     return {'recommendation': recommendation.get_by_id(client.user_id, recommendation_id)}
#
#
# @application.route('/recommendation/<int:recommendation_id>', methods=['POST'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def post_recommendation(client: Client, recommendation_id: int) -> dict:
#     raise NotImplementedError(request.path)
#
#
# @application.route('/recommendation/<int:recommendation_id>/<string:action>', methods=['PUT'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def put_recommendation_action(client: Client, recommendation_id: int, action: str) -> dict:
#     return {'recommendation': recommendation.put_action(client.user_id, recommendation_id, action)}
#
#
# @application.route('/recommendation/group', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_recommendation_groups(client: Client) -> dict:
#     return {'recommendation_group': recommendation.get_groups(**request.args)}
#
#
# @application.route('/recommendation/group/<int:group_id>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_recommendation_previous(client: Client, group_id: int) -> dict:
#     return {'recommendation': recommendation.get_previous(client.user_id, group_id)}
#
#
# @application.route('/object/type', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_object_types(client: Client) -> dict:
#     return {'object_type': object.get_types()}
#
#
# @application.route('/object/type/<id_or_name>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_object_type(client: Client, id_or_name: str) -> dict:
#     return {'object_type': object.get_type(id_or_name)}
#
#
# @application.route('/object/<id_or_name>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_object(client: Client, id_or_name: str) -> dict:
#     return {'object': object.get(id_or_name)}
#
#
# @application.route('/object', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_all_objects(client: Client) -> dict:
#     raise NotImplementedError(request.path)
#
#
# @application.route('/observation/<int:object_id>', methods=['GET'])
# @endpoint
# @authenticated
# @authorization(level=None)
# def get_observations_by_object(client: Client, object_id: int) -> dict:
#     return {'observation': observation.get_by_object(object_id)}
