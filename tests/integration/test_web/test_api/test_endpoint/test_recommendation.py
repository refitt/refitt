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
from contextlib import contextmanager

# internal libs
from refitt.database.model import Recommendation, RecommendationGroup, Facility
from refitt.web.api.response import STATUS, RESPONSE_MAP, NotFound, ParameterInvalid, PermissionDenied
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
