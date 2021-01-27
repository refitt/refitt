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

"""Database object_type model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import ObjectType, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestObjectType:
    """Tests for `ObjectType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create object_type instance and validate accessors."""
        for data in testdata['object_type']:
            object_type = ObjectType(**data)
            for key, value in data.items():
                assert getattr(object_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['object_type']:
            object_type = ObjectType.from_dict(data)
            assert data == object_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['object_type']:
            object_type = ObjectType.from_dict(data)
            assert tuple(data.values()) == object_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['object_type']:
            assert data == json_roundtrip(ObjectType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert ObjectType.from_name('SNIa').to_json(join=True) == {
            'id': 2,
            'name': 'SNIa',
            'description': 'WD detonation, Type Ia SN'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading object_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['object_type']):
            assert ObjectType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing object_type `id`."""
        with pytest.raises(NotFound):
            ObjectType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on object_type `id` already exists."""
        with pytest.raises(IntegrityError):
            ObjectType.add({'id': 1, 'name': 'Ludicrous Nova', 'description': 'The biggest ever'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading object_type from `name`."""
        for record in testdata['object_type']:
            assert ObjectType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing object_type `name`."""
        with pytest.raises(NotFound):
            ObjectType.from_name('Ludicrous SN')

    def test_name_already_exists(self) -> None:
        """Test exception on object_type `name` already exists."""
        with pytest.raises(IntegrityError):
            ObjectType.add({'name': 'SNIa', 'description': 'WD detonation, Type Ia SN'})
