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

"""Database recommendation_group model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import RecommendationGroup, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestRecommendationGroup:
    """Tests for `RecommendationGroup` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create recommendation_group instance and validate accessors."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup(**data)
            for key, value in data.items():
                assert getattr(recommendation_group, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup.from_dict(data)
            assert data == recommendation_group.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup.from_dict(data)
            assert tuple(data.values()) == recommendation_group.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['recommendation_group']:
            assert data == json_roundtrip(RecommendationGroup(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert RecommendationGroup.from_id(1).to_json(join=True) == {
            'id': 1,
            'created': '2020-10-24 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading recommendation_group from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['recommendation_group']):
            assert RecommendationGroup.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing recommendation_group `id`."""
        with pytest.raises(NotFound):
            RecommendationGroup.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on recommendation_group `id` already exists."""
        with pytest.raises(IntegrityError):
            RecommendationGroup.add({'id': 1})

    def test_new(self) -> None:
        """Test the creation of a new recommendation_group."""
        assert RecommendationGroup.count() == 3
        group = RecommendationGroup.new()
        assert RecommendationGroup.count() == 4
        RecommendationGroup.delete(group.id)
        assert RecommendationGroup.count() == 3

    def test_latest(self) -> None:
        """Test query for latest recommendation_group."""
        assert RecommendationGroup.latest().to_json(join=True) == {
            'id': 3,
            'created': '2020-10-26 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
        }

    def test_select_with_limit(self) -> None:
        """Test the selection of recommendation_group with a limit."""
        assert [group.to_json(join=True) for group in RecommendationGroup.select(limit=2)] == [
            {
                'id': 3,
                'created': '2020-10-26 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            },
            {
                'id': 2,
                'created': '2020-10-25 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            }
        ]

    def test_select_with_limit_and_offset(self) -> None:
        """Test the selection of recommendation_group with a limit and offset."""
        assert [group.to_json(join=True) for group in RecommendationGroup.select(limit=2, offset=1)] == [
            {
                'id': 2,
                'created': '2020-10-25 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            },
            {
                'id': 1,
                'created': '2020-10-24 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            }
        ]
