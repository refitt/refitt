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

"""Unit tests for RecommendationTag database model."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import RecommendationTag
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestRecommendationTag:
    """Unit tests for RecommendationTag model."""

    def test_init(self, testdata: TestData) -> None:
        """Create recommendation instance and validate accessors."""
        for data in testdata['recommendation_tag']:
            record = RecommendationTag(**data)
            for key, value in data.items():
                assert getattr(record, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['recommendation_tag']:
            record = RecommendationTag.from_dict(data)
            assert data == record.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['recommendation_tag']:
            record = RecommendationTag.from_dict(data)
            assert tuple(data.values()) == record.to_tuple()

    def test_get_names(self, testdata: TestData) -> None:
        """Test that we get the same sequence of tag names."""
        for i, data in enumerate(testdata['recommendation_tag']):
            assert data['name'] == RecommendationTag.get_name(i + 1)

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['recommendation_tag']:
            assert data == json_roundtrip(RecommendationTag(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert RecommendationTag.from_id(1).to_json(join=True) == {
            'id': 1,
            'object_id': 1,
            'name': 'determined_thirsty_cray',
            'object': {
                'id': 1,
                'type_id': 1,
                'aliases': {
                    'antares': 'ANT2020ae7t5xa',
                    'ztf': 'ZTF20actrfli',
                    'tag': 'determined_thirsty_cray'
                },
                'ra': 133.0164572,
                'dec': 44.80034109999999,
                'redshift': None,
                'data': {},
                'type': {
                    'id': 1,
                    'name': 'Unknown',
                    'description': 'Objects with unknown or unspecified type'
                },
            },
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading recommendation_tag from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['recommendation_tag']):
            assert RecommendationTag.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing recommendation_tag `id`."""
        with pytest.raises(RecommendationTag.NotFound):
            RecommendationTag.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on recommendation_tag `id` already exists."""
        with pytest.raises(IntegrityError):
            RecommendationTag.add({'id': 1, 'object_id': -1, 'name': 'foo_bar_baz'})

    def test_object_id_already_exists(self) -> None:
        """Test exception on recommendation_tag `object_id` already exists."""
        with pytest.raises(IntegrityError):
            RecommendationTag.add({'id': -1, 'object_id': 1, 'name': 'foo_bar_baz'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading recommendation_tag from `name`."""
        for i, record in enumerate(testdata['recommendation_tag']):
            assert RecommendationTag.from_name(record['name']).to_dict() == {**record, 'id': i + 1}

    def test_name_already_exists(self) -> None:
        """Test exception on recommendation_tag `name` already exists."""
        with pytest.raises(IntegrityError):
            RecommendationTag.add({'id': -1, 'object_id': 10, 'name': 'determined_thirsty_cray'})

    def test_relationship_object(self, testdata: TestData) -> None:
        """Test object foreign key relationship on recommendation_tag."""
        for i, record in enumerate(testdata['recommendation_tag']):
            assert RecommendationTag.from_id(i + 1).object.id == record['object_id']
