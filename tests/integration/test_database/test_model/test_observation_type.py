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

"""Database observation_type model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import ObservationType, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestObservationType:
    """Tests for `ObservationType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create observation_type instance and validate accessors."""
        for data in testdata['observation_type']:
            observation_type = ObservationType(**data)
            for key, value in data.items():
                assert getattr(observation_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['observation_type']:
            observation_type = ObservationType.from_dict(data)
            assert data == observation_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['observation_type']:
            observation_type = ObservationType.from_dict(data)
            assert tuple(data.values()) == observation_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['observation_type']:
            assert data == json_roundtrip(ObservationType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert ObservationType.from_name('g-ztf').to_json(join=True) == {
            'id': 2,
            'name': 'g-ztf',
            'units': 'mag',
            'description': 'G-band apparent magnitude (ZTF).'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading observation_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['observation_type']):
            assert ObservationType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing observation_type `id`."""
        with pytest.raises(NotFound):
            ObservationType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on observation_type `id` already exists."""
        with pytest.raises(IntegrityError):
            ObservationType.add({'id': 1, 'name': 'New Type', 'units': 'Kilo-Frobnicate',
                                 'description': 'A new filter type.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading observation_type from `name`."""
        for record in testdata['observation_type']:
            assert ObservationType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing observation_type `name`."""
        with pytest.raises(NotFound):
            ObservationType.from_name('Missing ObservationType Name')

    def test_name_already_exists(self) -> None:
        """Test exception on observation_type `name` already exists."""
        with pytest.raises(IntegrityError):
            ObservationType.add({'name': 'clear', 'units': 'mag',
                                 'description': 'Un-filtered apparent magnitude.'})
