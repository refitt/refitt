# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""REFITT's REST-API endpoint implementations."""

# internal libs
from ....database.model import Client
from ..app import application
from ..response import endpoint, NotFound
from ..auth import authenticated, authorization
from . import client, token, facility, user, object, source, observation, recommendation

# public interface
__all__ = []


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
