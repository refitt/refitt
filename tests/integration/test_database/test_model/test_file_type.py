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

"""Database file_type model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import FileType, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestFileType:
    """Tests for `FileType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create file_type instance and validate accessors."""
        for data in testdata['file_type']:
            file_type = FileType(**data)
            for key, value in data.items():
                assert getattr(file_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['file_type']:
            file_type = FileType.from_dict(data)
            assert data == file_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['file_type']:
            file_type = FileType.from_dict(data)
            assert tuple(data.values()) == file_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['file_type']:
            assert data == json_roundtrip(FileType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert FileType.from_name('fits.gz').to_json(join=True) == {
            'id': 1,
            'name': 'fits.gz',
            'description': 'Gzip compressed FITS file.'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading file_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['file_type']):
            assert FileType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing file_type `id`."""
        with pytest.raises(NotFound):
            FileType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on file_type `id` already exists."""
        with pytest.raises(IntegrityError):
            FileType.add({'id': 1, 'name': 'jpeg',
                          'description': 'A bad format for scientific images.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading file_type from `name`."""
        for record in testdata['file_type']:
            assert FileType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing file_type `name`."""
        with pytest.raises(NotFound):
            FileType.from_name('png')

    def test_name_already_exists(self) -> None:
        """Test exception on file_type `name` already exists."""
        with pytest.raises(IntegrityError):
            FileType.add({'name': 'fits.gz',
                          'description': 'Gzip compressed FITS file.'})
