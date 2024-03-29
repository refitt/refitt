# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""REFITT's REST-API endpoint implementations."""


# internal libs
from refitt.database.model import Client
from refitt.web.api.app import application
from refitt.web.api.response import endpoint, NotFound
from refitt.web.api.auth import authenticated, authorization
from refitt.web.api.endpoint import (
    client, token, facility, user, epoch,
    object, source, observation, recommendation, model
)

# public interface
__all__ = ['INFO', ]


INFO = {
    'token': token.info,
    'client': client.info,
    'user': user.info,
    'facility': facility.info,
    'object': object.info,
    'source': source.info,
    'observation': observation.info,
    'recommendation': recommendation.info,
    'epoch': epoch.info,
    'model': model.info,
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
