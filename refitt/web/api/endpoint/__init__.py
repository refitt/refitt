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

"""REFITT's REST-API endpoint implementations."""

# internal libs
from ....database.model import Client
from ..app import application
from ..response import endpoint, NotFound
from ..auth import authenticated, authorization
from . import client, token, facility, user, object, source, observation, recommendation


INFO = {
    'token': token.info,
    'client': client.info,
    'user': user.info,
    'facility': facility.info,
    'object': object.info,
    'source': source.info,
    'observation': observation.info,
    'recommendation': recommendation.info,
}


@application.route('/info', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_all_info(client: Client) -> dict:  # noqa: client not used
    return INFO


@application.route('/info/<resource>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_resource_info(client: Client, resource: str) -> dict:  # noqa: client not used
    try:
        return INFO[resource]
    except KeyError as error:
        raise NotFound(f'No info for resource \'{resource}\'') from error
