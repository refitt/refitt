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

"""Database source model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Source, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestSource:
    """Tests for `Source` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create source instance and validate accessors."""
        for data in testdata['source']:
            source = Source(**data)
            for key, value in data.items():
                assert getattr(source, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['source']:
            source = Source.from_dict(data)
            assert data == source.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['source']:
            source = Source.from_dict(data)
            assert tuple(data.values()) == source.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['source']:
            assert data == json_roundtrip(Source(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Source.from_name('antares').to_json(join=True) == {
            'id': 2,
            'type_id': 3,
            'facility_id': None,
            'user_id': None,
            'name': 'antares',
            'description': 'Antares is an alert broker developed by NOAO for ZTF and LSST.',
            'data': {},
            'type': {
                'id': 3,
                'name': 'broker',
                'description': 'Alerts from data brokers.'
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading source from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['source']):
            assert Source.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing source `id`."""
        with pytest.raises(NotFound):
            Source.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on source `id` already exists."""
        with pytest.raises(IntegrityError):
            Source.add({'id': 1, 'type_id': 1, 'facility_id': None, 'user_id': None,
                        'name': 'other', 'description': '...', 'data': {}})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading source from `name`."""
        for record in testdata['source']:
            assert Source.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing source `name`."""
        with pytest.raises(NotFound):
            Source.from_name('Missing Source Name')

    def test_name_already_exists(self) -> None:
        """Test exception on source `name` already exists."""
        with pytest.raises(IntegrityError):
            Source.add({'type_id': 1, 'facility_id': None, 'user_id': 1, 'name': 'refitt',
                        'description': '...', 'data': {}})

    def test_relationship_source_type(self, testdata: TestData) -> None:
        """Test source foreign key relationship on source_type."""
        for i, record in enumerate(testdata['source']):
            assert Source.from_id(i + 1).type.id == record['type_id']
