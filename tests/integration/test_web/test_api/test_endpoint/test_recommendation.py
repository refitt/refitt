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
from io import BytesIO
from datetime import datetime
from abc import ABC, abstractproperty
from contextlib import contextmanager

# external libs
import pytest

# internal libs
from refitt.database.model import Recommendation, RecommendationGroup, User, Facility, Observation, File
from refitt.web.api.response import (STATUS, RESPONSE_MAP, NotFound, ParameterInvalid, ParameterNotFound,
                                     PermissionDenied, PayloadTooLarge, PayloadMalformed)
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


class TestGetPredicted(RecommendationEndpoint):
    relation = 'predicted'


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


class TestGetObserved(RecommendationEndpoint):
    relation = 'observed'


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


@contextmanager
def temp_remove_observation_and_file(file_id: int) -> None:
    """Remove records from database temporarily."""
    file = File.from_id(file_id)
    file_data = file.to_dict()
    obs_data = file.observation.to_dict()
    rec_id = Recommendation.query().filter_by(observation_id=obs_data['id']).one().id
    try:
        Recommendation.update(rec_id, observation_id=None)  # remove fkey relationship
        File.delete(file_data['id'])
        Observation.delete(obs_data['id'])
        yield
    finally:
        Observation.add(obs_data)
        File.add(file_data)
        Recommendation.update(rec_id, observation_id=obs_data['id'])


@contextmanager
def temp_remove_file(file_id: int) -> None:
    """Remove records from database temporarily."""
    data = File.from_id(file_id).to_dict()
    try:
        File.delete(data['id'])
        yield
    finally:
        File.add(data)


class TestGetRecommendationObservedFile(Endpoint):
    """Tests for GET /recommendation/<id>/observed/file endpoint."""

    route: str = '/recommendation/22/observed/file'  # NOTE: last returned by tomb_raider
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def recommendation_id(self) -> int:
        """Recommendation ID from `route`."""
        return int(self.route.split('/')[2])

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_permission_denied(self) -> None:
        rec = Recommendation.for_user(User.from_alias('delta_one').id)[-1]  # NOTE: not tomb_raider
        assert self.get(f'/recommendation/{rec.id}/observed/file',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public'
            }
        )

    def test_recommendation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/recommendation/0/observed/file', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0',
            }
        )

    def test_observation_not_found(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file_id = File.from_observation(rec.observation_id).id
        with temp_remove_observation_and_file(file_id):
            client = self.get_client(self.user)
            assert self.get(f'/recommendation/{self.recommendation_id}/observed/file', client_id=client.id) == (
                RESPONSE_MAP[NotFound], {
                    'Status': 'Error',
                    'Message': 'Missing observation record, cannot get file',
                }
            )

    def test_get_file(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file = File.from_observation(rec.observation_id)
        client = self.get_client(self.user)
        route = f'/recommendation/{self.recommendation_id}/observed/file'
        assert self.get(route, client_id=client.id, response_type='file') == (
            STATUS['OK'], {f'observation_{file.observation_id}.fits.gz': file.data}
        )


class TestPostRecommendationObservedFile(Endpoint):
    """Tests for POST /recommendation/<id>/observed/file endpoint."""

    route: str = '/recommendation/22/observed/file'  # NOTE: last returned by tomb_raider
    method: str = 'post'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def recommendation_id(self) -> int:
        """Recommendation ID from `route`."""
        return int(self.route.split('/')[2])

    def test_invalid_parameter(self) -> None:
        assert self.post(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_permission_denied(self) -> None:
        rec = Recommendation.for_user(User.from_alias('delta_one').id)[-1]  # NOTE: not tomb_raider
        assert self.post(f'/recommendation/{rec.id}/observed/file',
                         client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public'
            }
        )

    def test_recommendation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.post(f'/recommendation/0/observed/file', client_id=client.id,
                         files={'obs.fits.gz': BytesIO(b'abc'), }) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0',
            }
        )

    def test_filetype_not_supported(self) -> None:
        client = self.get_client(self.user)
        assert self.post(f'/recommendation/{self.recommendation_id}/observed/file', client_id=client.id,
                         files={'data.foo': BytesIO(b'abc'), }) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'File type \'foo\' not supported',
            }
        )

    def test_observation_not_found(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file_id = File.from_observation(rec.observation_id).id
        with temp_remove_observation_and_file(file_id):
            client = self.get_client(self.user)
            assert self.post(f'/recommendation/{self.recommendation_id}/observed/file', client_id=client.id,
                             files={'obs.fits.gz': BytesIO(b'abc'), }) == (
                RESPONSE_MAP[NotFound], {
                    'Status': 'Error',
                    'Message': 'Missing observation record, cannot upload file',
                }
            )

    def test_successful_post_file(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file_id = File.from_observation(rec.observation_id).id
        with temp_remove_file(file_id):
            client = self.get_client(self.user)
            status, payload = self.post(f'/recommendation/{self.recommendation_id}/observed/file', client_id=client.id,
                                        files={'obs.fits.gz': BytesIO(b'abc'), })
            assert status == STATUS['OK']
            assert 'Status' in payload and payload['Status'] == 'Success'
            assert 'Response' in payload and 'file' in payload['Response'] and 'id' in payload['Response']['file']
            assert isinstance(payload['Response']['file']['id'], int)
            assert list(payload['Response']['file'].keys()) == ['id', ]
            new_file_id = int(payload['Response']['file']['id'])
            File.delete(new_file_id)  # NOTE: remove "new" file
            with pytest.raises(File.NotFound):
                File.from_id(new_file_id)

    def test_successful_update_file(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file = File.from_observation(rec.observation_id)
        client = self.get_client(self.user)
        route = f'/recommendation/{self.recommendation_id}/observed/file'
        # check original file
        assert self.get(route, client_id=client.id, response_type='file') == (
            STATUS['OK'], {f'observation_{file.observation_id}.fits.gz': file.data}
        )
        # post new file
        assert self.post(route, client_id=client.id,
                         files={'obs.fits.gz': BytesIO(b'abc'), }) == (
            STATUS['OK'],
            {'Status': 'Success',
             'Response': {'file': {'id': file.id}}}  # NOTE: original file ID
        )
        # check new file content is persisted
        assert self.get(route, client_id=client.id, response_type='file') == (
            STATUS['OK'], {f'observation_{file.observation_id}.fits.gz': b'abc'}
        )
        # restore original file
        assert self.post(route, client_id=client.id,
                         files={'obs.fits.gz': BytesIO(file.data), }) == (
            STATUS['OK'],
            {'Status': 'Success',
             'Response': {'file': {'id': file.id}}}  # NOTE: original file ID
        )
        # check original file is restored
        assert self.get(route, client_id=client.id, response_type='file') == (
            STATUS['OK'], {f'observation_{file.observation_id}.fits.gz': file.data}
        )


class TestGetRecommendationObservedFileType(Endpoint):
    """Tests for GET /recommendation/<id>/observed/file/type endpoint."""

    route: str = '/recommendation/22/observed/file/type'  # NOTE: last returned by tomb_raider
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def recommendation_id(self) -> int:
        """Recommendation ID from `route`."""
        return int(self.route.split('/')[2])

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_permission_denied(self) -> None:
        rec = Recommendation.for_user(User.from_alias('delta_one').id)[-1]  # NOTE: not tomb_raider
        assert self.get(f'/recommendation/{rec.id}/observed/file/type',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public'
            }
        )

    def test_recommendation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/recommendation/0/observed/file/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0',
            }
        )

    def test_observation_not_found(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file_id = File.from_observation(rec.observation_id).id
        with temp_remove_observation_and_file(file_id):
            client = self.get_client(self.user)
            assert self.get(f'/recommendation/{self.recommendation_id}/observed/file/type', client_id=client.id) == (
                RESPONSE_MAP[NotFound], {
                    'Status': 'Error',
                    'Message': 'Missing observation record, cannot get file',
                }
            )

    def test_get_file_type(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        file = File.from_observation(rec.observation_id)
        client = self.get_client(self.user)
        route = f'/recommendation/{self.recommendation_id}/observed/file/type'
        assert self.get(route, client_id=client.id) == (
            STATUS['OK'],
            {'Status': 'Success',
             'Response': {'file_type': file.type.to_json()}}
        )


class TestPostRecommendationObserved(Endpoint):
    """Tests for POST /recommendation/<id>/observed endpoint."""

    route: str = '/recommendation/22/observed'  # NOTE: last returned by tomb_raider
    method: str = 'post'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def recommendation_id(self) -> int:
        """Recommendation ID from `route`."""
        return int(self.route.split('/')[2])

    def test_invalid_parameter(self) -> None:
        assert self.post(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_permission_denied(self) -> None:
        rec = Recommendation.for_user(User.from_alias('delta_one').id)[-1]  # NOTE: not tomb_raider
        assert self.post(f'/recommendation/{rec.id}/observed/file',
                         client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Recommendation is not public'
            }
        )

    def test_recommendation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.post(f'/recommendation/0/observed', client_id=client.id,
                         json={'type_id': 1, 'value': 3.14, 'error': None,
                               'time': str(datetime.now().astimezone())}) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No recommendation with id=0',
            }
        )

    def test_missing_payload(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id, ) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Missing data in request',
            }
        )

    def test_malformed_payload(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id, data=b'abc') == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Invalid JSON data',
            }
        )

    def test_missing_type_id(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'value': 3.14, 'error': None, 'time': str(datetime.now().astimezone())}) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Missing required field \'type_id\'',
            }
        )

    def test_missing_value(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'type_id': 1, 'error': None, 'time': str(datetime.now().astimezone())}) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Missing required field \'value\'',
            }
        )

    def test_missing_error(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'type_id': 1, 'value': 3.14, 'time': str(datetime.now().astimezone())}) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Missing required field \'error\'',
            }
        )

    def test_missing_time(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'type_id': 1, 'value': 3.14, 'error': None, }) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Missing required field \'time\'',
            }
        )

    def test_malformed_time(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'type_id': 1, 'value': 3.14, 'error': None, 'time': 'abc'}) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Invalid isoformat string: \'abc\'',
            }
        )

    def test_unexpected_field(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id,
                         json={'type_id': 1, 'value': 3.14, 'error': None, 'foo': True,
                               'time': str(datetime.now().astimezone())}) == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Unexpected field \'foo\'',
            }
        )

    def test_successful_update_observation(self) -> None:
        rec = Recommendation.from_id(self.recommendation_id)
        original = rec.observed.to_json()
        new_data = {'type_id': 1, 'value': 3.14, 'error': None,
                    'time': str(datetime.now().astimezone())}
        client = self.get_client(self.user)
        # update data
        just_prior = str(datetime.now().astimezone())  # ISO format
        status, payload = self.post(self.route, client_id=client.id, json=new_data)
        assert status == STATUS['OK']
        for field, value in new_data.items():
            assert payload.get('Response').get('observation').get(field) == value
        assert just_prior < payload.get('Response').get('observation').get('recorded')
        # restore original data
        original_id = original.pop('id')
        Observation.update(original_id, **original)  # NOTE: 'value' is updated but then reverts on commit?!
        Observation.update(original_id, value=original['value'])  # FIXME: WTF SQLAlchemy?
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'observation': {'id': original_id, **original}}}
        )

    def test_new_observation(self) -> None:
        # temporarily remove existing file to simulate adding "new" observation
        rec = Recommendation.from_id(self.recommendation_id)
        original = rec.observed.to_json()
        new_data = {'type_id': 1, 'value': 3.14, 'error': None,
                    'time': str(datetime.now().astimezone())}
        file_id = File.from_observation(rec.observation_id).id
        client = self.get_client(self.user)
        with temp_remove_observation_and_file(file_id):
            status, response = self.post(self.route, client_id=client.id, json=new_data)
            assert status == STATUS['OK']
            new_id = response['Response']['observation']['id']
            # check new data is persisted (NOTE: not easy to test 'recorded' timestamp
            status, payload = self.get(self.route, client_id=client.id)
            assert status == STATUS['OK']
            for field, value in new_data.items():
                assert payload['Response']['observation'][field] == value
            # delete new observation
            Recommendation.update(rec.id, observation_id=None)
            Observation.delete(new_id)
        # check old data is restored
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {'Status': 'Success',
                           'Response': {'observation': original}}
        )
