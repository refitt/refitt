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

"""Database source_type model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import SourceType, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestSourceType:
    """Tests for `SourceType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create source_type instance and validate accessors."""
        for data in testdata['source_type']:
            source_type = SourceType(**data)
            for key, value in data.items():
                assert getattr(source_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['source_type']:
            source_type = SourceType.from_dict(data)
            assert data == source_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['source_type']:
            source_type = SourceType.from_dict(data)
            assert tuple(data.values()) == source_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['source_type']:
            assert data == json_roundtrip(SourceType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert SourceType.from_name('catalog').to_json(join=True) == {
            'id': 2,
            'name': 'catalog',
            'description': 'Real observations from external catalogs.'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading source_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['source_type']):
            assert SourceType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing source_type `id`."""
        with pytest.raises(NotFound):
            SourceType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on source_type `id` already exists."""
        with pytest.raises(IntegrityError):
            SourceType.add({'id': 2, 'name': 'other catalog',
                            'description': 'Real observations from external catalogs.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading source_type from `name`."""
        for record in testdata['source_type']:
            assert SourceType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing source_type `name`."""
        with pytest.raises(NotFound):
            SourceType.from_name('Missing SourceType Name')

    def test_name_already_exists(self) -> None:
        """Test exception on source_type `name` already exists."""
        with pytest.raises(IntegrityError):
            SourceType.add({'name': 'catalog',
                            'description': 'Real observations from external catalogs.'})
