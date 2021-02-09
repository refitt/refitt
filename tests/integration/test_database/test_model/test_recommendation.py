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

"""Database recommendation model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import (Recommendation, RecommendationGroup, RecommendationTag,
                                   User, Facility, Object, Forecast, Observation, NotFound)
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestRecommendation:
    """Tests for `Recommendation` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create recommendation instance and validate accessors."""
        for data in testdata['recommendation']:
            recommendation = Recommendation(**data)
            for key, value in data.items():
                assert getattr(recommendation, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['recommendation']:
            recommendation = Recommendation.from_dict(data)
            assert data == recommendation.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['recommendation']:
            recommendation = Recommendation.from_dict(data)
            assert tuple(data.values()) == recommendation.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['recommendation']:
            assert data == json_roundtrip(Recommendation(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert Recommendation.from_id(1).to_json(join=True) == {
            'id': 1,
            'group_id': 1,
            'tag_id': 1,
            'time': '2020-10-24 20:02:00' + ('' if config.backend == 'sqlite' else '-04:00'),
            'priority': 1,
            'object_id': 1,
            'facility_id': 1,
            'user_id': 2,
            'forecast_id': 1,
            'predicted_observation_id': 11,
            'observation_id': 19,
            'accepted': True,
            'rejected': False,
            'data': {},
            'group': RecommendationGroup.from_id(1).to_json(join=True),
            'tag': RecommendationTag.from_id(1).to_json(join=True),
            'user': User.from_id(2).to_json(join=True),
            'facility': Facility.from_id(1).to_json(join=True),
            'object': Object.from_id(1).to_json(join=True),
            'forecast': Forecast.from_id(1).to_json(join=True),
            'predicted': Observation.from_id(11).to_json(join=True),
            'observed': Observation.from_id(19).to_json(join=True),
            }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading recommendation from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing recommendation `id`."""
        with pytest.raises(NotFound):
            Recommendation.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on recommendation `id` already exists."""
        with pytest.raises(IntegrityError):
            Recommendation.add({'id': 1, 'group_id': 1, 'tag_id': 1, 'priority': 1, 'object_id': 1,
                                'facility_id': 1, 'user_id': 2})

    def test_relationship_group(self, testdata: TestData) -> None:
        """Test recommendation_group foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).group.id == record['group_id']

    def test_relationship_object(self, testdata: TestData) -> None:
        """Test object foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).object.id == record['object_id']

    def test_relationship_facility(self, testdata: TestData) -> None:
        """Test facility foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).facility.id == record['facility_id']

    def test_relationship_user(self, testdata: TestData) -> None:
        """Test user foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).user.id == record['user_id']

    def test_relationship_forecast(self, testdata: TestData) -> None:
        """Test forecast foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).forecast.id == record['forecast_id']

    def test_relationship_predicted(self, testdata: TestData) -> None:
        """Test predicted observation foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).predicted.id == record['predicted_observation_id']

    def test_relationship_observed(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on recommendation."""
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).observed.id == record['observation_id']

    def test_for_user(self) -> None:
        """Test query for all recommendations for a given user."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 3

    def test_for_user_with_group_id(self) -> None:
        """Test query for all recommendations for a given user and group."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id, group_id=3)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 3

    def test_for_user_with_group_id_2(self) -> None:
        """Test query for all recommendations for a given user and group."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id, group_id=2)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 2

    def test_next(self) -> None:
        """Test query for latest recommendation."""

        user_id = User.from_alias('tomb_raider').id
        response = Recommendation.next(user_id=user_id)
        assert len(response) == 0  # NOTE: all accepted already

        rec_id = Recommendation.for_user(user_id)[0].id
        Recommendation.update(rec_id, accepted=False)

        response = Recommendation.next(user_id=user_id)
        assert len(response) == 1

        Recommendation.update(rec_id, accepted=True)
        response = Recommendation.next(user_id=user_id)
        assert len(response) == 0

    def test_history(self) -> None:
        """Test query for previously interacted with recommendations."""

        user_id = User.from_alias('tomb_raider').id
        records = Recommendation.history(user_id=user_id, group_id=3)
        assert all(isinstance(r, Recommendation) for r in records)
        assert len(records) == 4  # NOTE: all accepted already
        assert all(r.accepted for r in records)

        rec_id = Recommendation.for_user(user_id)[0].id
        Recommendation.update(rec_id, accepted=False)

        records = Recommendation.history(user_id=user_id, group_id=3)
        assert len(records) == 3
        assert all(r.accepted for r in records)

        # restore state of database
        Recommendation.update(rec_id, accepted=True)
        records = Recommendation.history(user_id=user_id, group_id=3)
        assert len(records) == 4
        assert all(r.accepted for r in records)
