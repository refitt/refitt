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

"""REFITT's API /recommendation end-point implementation."""

# type annotations
from typing import List, Dict, Any

# internal libs
from ..exceptions import PermissionDenied
from ....database import execute
from ....database.recommendation import Recommendation, RecommendationGroup


def get(user_id: int, **request_params) -> List[Dict[str, Any]]:
    """Make call to `Recommendation.select`."""

    params = {}
    if 'group' in request_params:
        params['group'] = request_params.pop('group')
    if 'limit' in request_params:
        params['limit'] = int(request_params.pop('limit'))
    if 'facility_id' in request_params:
        params['facility_id'] = int(request_params.pop('facility_id'))
    if 'limiting_magnitude' in request_params:
        params['limiting_magnitude'] = float(request_params.pop('limiting_magnitude'))

    if request_params:
        for field, value in request_params.items():
            raise AttributeError(f'"{field}" not a valid parameter for /recommendation')

    return [recommendation.embed()
            for recommendation in Recommendation.select(user_id, **params)]


def get_by_id(user_id, recommendation_id: int) -> Dict[str, Any]:
    """Select a single recommendation by its unique identifier."""
    recommendation =  Recommendation.select_by_id(recommendation_id)
    if recommendation.user_id == user_id:
        return recommendation.embed()
    else:
        raise PermissionDenied(f'recommendation not for user_id={user_id}')


ACCEPT_RECOMMENDATION = """\
UPDATE
    recommendation.recommendation
SET
    recommendation_accepted = true,
    recommendation_rejected = false
WHERE
    recommendation_id = :recommendation_id
"""


REJECT_RECOMMENDATION = """\
UPDATE
    recommendation.recommendation
SET
    recommendation_accepted = false,
    recommendation_rejected = true
WHERE
    recommendation_id = :recommendation_id
"""


RESET_RECOMMENDATION = """\
UPDATE
    recommendation.recommendation
SET
    recommendation_accepted = false,
    recommendation_rejected = false
WHERE
    recommendation_id = :recommendation_id
"""


ACTIONS = {'accept': ACCEPT_RECOMMENDATION,
           'reject': REJECT_RECOMMENDATION,
           'reset': RESET_RECOMMENDATION}


def put_action(user_id, recommendation_id: int, action: str) -> dict:
    """
    Claim some action against the identified recommendation.
    You can /accept, /reject/ or /reset a recommendation.
    """

    recommendation =  Recommendation.from_id(recommendation_id)
    if recommendation.user_id != user_id:
        raise PermissionDenied(f'recommendation not for user_id={user_id}')

    try:
        execute(ACTIONS[action], recommendation_id=recommendation_id)
    except KeyError as error:
        raise AttributeError(f'/{action} not valid') from error

    return {'recommendation_id': recommendation_id}


def get_groups(**request_params) -> list:
    """Get listing of available recommendation groups."""

    params = {}
    params['limit'] = int(request_params.pop('limit', 1))
    if 'before' in request_params:
        params['before'] = int(request_params.pop('before'))
    if 'after' in request_params:
        params['after'] = int(request_params.pop('after'))

    if request_params:
        for field, value in request_params.items():
            raise AttributeError(f'"{field}" not a valid parameter for /recommendation/group')

    return [recommendation_group.embed()
            for recommendation_group in RecommendationGroup.select(**params)]


def get_previous(user_id: int, group_id: int) -> dict:
    """Get listing of previously seen recommendations."""
    return [recommendation.embed()
            for recommendation in Recommendation.select_group(user_id, group_id)]
