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

"""Integration tests for /recommendation endpoints."""


# standard libs
from abc import ABC, abstractproperty
from contextlib import contextmanager

# internal libs
from refitt.database.model import Recommendation, RecommendationGroup, Facility
from refitt.web.api.response import (STATUS, RESPONSE_MAP, NotFound, ParameterInvalid,
                                     ParameterNotFound, PermissionDenied, PayloadTooLarge)
from refitt.web.api.endpoint.recommendation import recommendation_slices
from tests.integration.test_web.test_api.test_endpoint import Endpoint


@contextmanager
def all_unseen(user_id: int, group_id: int) -> None:
    """Temporarily set `accept` and `reject` to false."""
    previous = {
        record.id: (record.accepted, record.rejected)
        for record in Recommendation.query().filter_by(user_id=user_id, group_id=group_id).all()
    }
    try:
        for id in previous:
            Recommendation.update(id, accepted=False, rejected=False)
        yield
    finally:
        for id, (accepted, rejected) in previous.items():
            Recommendation.update(id, accepted=accepted, rejected=rejected)


class TestGetNextRecommendation(Endpoint):
    """Tests for GET /recommendation endpoint."""

    route: str = '/recommendation'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_all_accepted(self) -> None:
        """Should be empty if all are already accepted/rejected (as in test data)."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {
                    'recommendation': [],
                }
            }
        )

    def test_all_unseen(self) -> None:
        """Should get all recommendations for the user if none have been accepted or rejected."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        with all_unseen(user_id=client.user_id, group_id=group_id):
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id)
            assert len(recommendations) == 4
            assert self.get(self.route, client_id=client.id) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json() for r in recommendations],
                    }
                }
            )

    def test_with_limit(self) -> None:
        """Should only return the first recommendation of the unseen for given group."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        with all_unseen(user_id=client.user_id, group_id=group_id):
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id, limit=1)
            assert len(recommendations) == 1
            assert self.get(self.route, client_id=client.id, limit=1) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json() for r in recommendations],
                    }
                }
            )

    def test_with_facility(self) -> None:
        """Only return recommendations for the given facility."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        with all_unseen(user_id=client.user_id, group_id=group_id):
            facility = Facility.from_name('Croft_1m')
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id,
                                                  facility_id=facility.id)
            assert len(recommendations) == 2
            assert all(recommendation.group_id == group_id for recommendation in recommendations)
            assert all(recommendation.facility_id == facility.id for recommendation in recommendations)
            assert self.get(self.route, client_id=client.id, facility_id=facility.id) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json() for r in recommendations],
                    }
                }
            )

    def test_with_facility_and_limiting_magnitude(self) -> None:
        """Only return recommendations for the given facility and limiting magnitude."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        with all_unseen(user_id=client.user_id, group_id=group_id):
            facility = Facility.from_name('Croft_1m')
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id,
                                                  facility_id=facility.id, limiting_magnitude=15.4)
            assert len(recommendations) == 1
            assert all(recommendation.group_id == group_id for recommendation in recommendations)
            assert all(recommendation.facility_id == facility.id for recommendation in recommendations)
            assert recommendations[0].predicted.value <= 15.4
            assert self.get(self.route, client_id=client.id, facility_id=facility.id, limiting_magnitude=15.4) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json() for r in recommendations],
                    }
                }
            )

    def test_with_group(self) -> None:
        """Return recommendations for a specified group."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        group_id = 2  # the previous group instead
        with all_unseen(user_id=client.user_id, group_id=group_id):
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id)
            assert len(recommendations) == 4
            assert all(recommendation.group_id == group_id for recommendation in recommendations)
            assert self.get(self.route, client_id=client.id, group_id=group_id) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json() for r in recommendations],
                    }
                }
            )

    def test_with_join(self) -> None:
        """Return recommendations for a specified group."""
        client = self.get_client(self.user)
        group_id = RecommendationGroup.latest().id
        assert group_id == 3
        with all_unseen(user_id=client.user_id, group_id=group_id):
            recommendations = Recommendation.next(user_id=client.user_id, group_id=group_id, limit=1)
            assert len(recommendations) == 1
            assert all(recommendation.group_id == group_id for recommendation in recommendations)
            assert self.get(self.route, client_id=client.id, limit=1, join=True) == (
                STATUS['OK'], {
                    'Status': 'Success',
                    'Response': {
                        'recommendation': [r.to_json(join=True) for r in recommendations],
                    }
                }
            )


class TestGetRecommendation(Endpoint):
    """Tests for GET /recommendation/<id> endpoint."""

    route: str = '/recommendation/3'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_permission_denied(self) -> None:
        assert self.get('/recommendation/1', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public',
            }
        )

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_not_found(self) -> None:
        assert self.get('/recommendation/0', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0'
            }
        )

    def test_get(self) -> None:
        data = Recommendation.from_id(3).to_json()
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation': data},
            }
        )

    def test_get_with_join(self) -> None:
        data = Recommendation.from_id(3).to_json(join=True)
        assert self.get(self.route, client_id=self.get_client(self.user).id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation': data},
            }
        )


class TestPutRecommendationAttribute(Endpoint):
    """Tests for PUT /recommendation/<id> endpoint."""

    route: str = '/recommendation/3'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_permission_denied(self) -> None:
        assert self.put('/recommendation/1', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public',
            }
        )

    def test_invalid_parameter(self) -> None:
        assert self.put(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_not_found(self) -> None:
        assert self.put('/recommendation/0', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0'
            }
        )

    def test_accept(self) -> None:
        client = self.get_client(self.user)
        with all_unseen(client.user_id, group_id=1):
            assert Recommendation.from_id(3).accepted == False
            assert self.put(self.route, client_id=client.id, accepted=True) == (
                STATUS['OK'], {'Status': 'Success', 'Response': {}})
            assert Recommendation.from_id(3).accepted == True

    def test_reject(self) -> None:
        client = self.get_client(self.user)
        with all_unseen(client.user_id, group_id=1):
            assert Recommendation.from_id(3).rejected == False
            assert self.put(self.route, client_id=client.id, rejected=True) == (
                STATUS['OK'], {'Status': 'Success', 'Response': {}})
            assert Recommendation.from_id(3).rejected == True


class RecommendationEndpoint(Endpoint, ABC):
    """Base class for GET /recommendation/<id>/<relation> endpoints."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @abstractproperty
    def relation(self) -> str:
        """E.g., 'object/type'."""

    @property
    def route(self) -> str:
        return f'/recommendation/3/{self.relation}'

    def test_permission_denied(self) -> None:
        assert self.get(f'/recommendation/1/{self.relation}', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public',
            }
        )

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_not_found(self) -> None:
        assert self.get(f'/recommendation/0/{self.relation}', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0'
            }
        )

    def test_get(self) -> None:
        resource, get_member = recommendation_slices[self.relation]
        recommendation = Recommendation.from_id(3)
        data = get_member(recommendation).to_json(join=False)
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {resource: data},
            }
        )

    def test_get_with_join(self) -> None:
        resource, get_member = recommendation_slices[self.relation]
        recommendation = Recommendation.from_id(3)
        data = get_member(recommendation).to_json(join=True)
        assert self.get(self.route, client_id=self.get_client(self.user).id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {resource: data},
            }
        )


class TestGetGroup(RecommendationEndpoint):
    relation = 'group'


class TestGetTag(RecommendationEndpoint):
    relation = 'tag'


class TestGetUser(RecommendationEndpoint):
    relation = 'user'


class TestGetFacility(RecommendationEndpoint):
    relation = 'facility'


class TestGetObject(RecommendationEndpoint):
    relation = 'object'


class TestGetObjectType(RecommendationEndpoint):
    relation = 'object/type'


class TestGetForecast(RecommendationEndpoint):
    relation = 'forecast'


class TestGetPredictedType(RecommendationEndpoint):
    relation = 'predicted/type'


class TestGetPredictedObject(RecommendationEndpoint):
    relation = 'predicted/object'


class TestGetPredictedObjectType(RecommendationEndpoint):
    relation = 'predicted/object/type'


class TestGetPredictedSource(RecommendationEndpoint):
    relation = 'predicted/source'


class TestGetPredictedSourceType(RecommendationEndpoint):
    relation = 'predicted/source/type'


class TestGetPredictedUser(RecommendationEndpoint):
    relation = 'predicted/source/user'


class TestGetObservedType(RecommendationEndpoint):
    relation = 'observed/type'


class TestGetObservedObject(RecommendationEndpoint):
    relation = 'observed/object'


class TestGetObservedObjectType(RecommendationEndpoint):
    relation = 'observed/object/type'


class TestGetObservedSource(RecommendationEndpoint):
    relation = 'observed/source'


class TestGetObservedSourceType(RecommendationEndpoint):
    relation = 'observed/source/type'


class TestGetObservedUser(RecommendationEndpoint):
    relation = 'observed/source/user'


class TestGetObservedFacility(RecommendationEndpoint):
    relation = 'observed/source/facility'


class TestGetRecommendationHistory(Endpoint):
    """Tests for GET /recommendation/history endpoint."""

    route: str = '/recommendation/history'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, group_id=3, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_group_id_missing(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Missing expected parameter: group_id'
            }
        )

    def test_group_id_not_integer(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, group_id='abc') == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Expected integer for parameter: group_id'
            }
        )

    def test_get_group_3(self) -> None:
        history = Recommendation.history(user_id=3, group_id=3)
        assert len(history) == 4
        assert all(recommendation.accepted for recommendation in history)
        assert all(recommendation.group_id == 3 for recommendation in history)
        assert self.get(self.route, client_id=self.get_client(self.user).id, group_id=3) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation': [recommendation.to_json() for recommendation in history]},
            }
        )

    def test_get_group_2(self) -> None:
        history = Recommendation.history(user_id=3, group_id=2)
        assert len(history) == 4
        assert all(recommendation.accepted for recommendation in history)
        assert all(recommendation.group_id == 2 for recommendation in history)
        assert self.get(self.route, client_id=self.get_client(self.user).id, group_id=2) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation': [recommendation.to_json() for recommendation in history]},
            }
        )


class TestGetRecommendationGroupMany(Endpoint):
    """Tests for GET /recommendation/group/ endpoint."""

    route: str = '/recommendation/group'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=1, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_limit_missing(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Missing expected parameter: limit'
            }
        )

    def test_limit_too_large(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=1000) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': 'Must provide \'limit\' less than 100'
            }
        )

    def test_limit_not_integer(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit='abc') == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Expected integer for parameter: limit'
            }
        )

    def test_offset_not_integer(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=4, offset='abc') == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Expected integer for parameter: offset'
            }
        )

    def test_get_all(self) -> None:
        data = [group.to_json() for group in RecommendationGroup.select(20)]
        assert len(data) == 3
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=20) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation_group': data},
            }
        )

    def test_get_with_limit(self) -> None:
        data = [group.to_json() for group in RecommendationGroup.select(20)]
        assert len(data) == 3
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation_group': data[:2]},
            }
        )

    def test_get_with_offset_1(self) -> None:
        data = [group.to_json() for group in RecommendationGroup.select(20)]
        assert len(data) == 3
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2, offset=1) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation_group': data[1:]},
            }
        )

    def test_get_with_offset_2(self) -> None:
        data = [group.to_json() for group in RecommendationGroup.select(20)]
        assert len(data) == 3
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2, offset=2) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation_group': data[2:]},
            }
        )


class TestGetRecommendationGroup(Endpoint):
    """Tests for GET /recommendation/group/<id> endpoint."""

    route: str = '/recommendation/group/1'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_not_found(self) -> None:
        assert self.get('/recommendation/group/0', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation_group with id=0'
            }
        )

    def test_get(self) -> None:
        data = RecommendationGroup.from_id(1).to_json()
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'recommendation_group': data},
            }
        )
