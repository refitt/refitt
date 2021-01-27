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

"""Database file model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import File, FileType, Observation, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestFile:
    """Tests for `File` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create file instance and validate accessors."""
        for data in testdata['file']:
            file = File(**data)
            for key, value in data.items():
                assert getattr(file, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['file']:
            file = File.from_dict(data)
            assert data == file.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['file']:
            file = File.from_dict(data)
            assert tuple(data.values()) == file.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['file']:
            assert data == json_roundtrip(File(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert File.from_id(1).to_json(join=True) == {
            'id': 1,
            'observation_id': 19,
            'type_id': 1,
            'data': ['H4sICIVdxV8C/2xvY2FsXzMuZml0cwAAAAD//+zRMQrCMBjF8au8G2iLuDkoRghoKSRD1mhS6JBE',
                     'kjj09lbBLUEKHb/fAf48eILf+isDDiiQ2OAR/BCiS8gBFy4FUtbe6GhQdOKy56rc2+/mno5RTzA6',
                     'a+TpafFHd1RcoLKvnXv+5e42Igy/8uisT2Pwqd5ryr1mi8W+vXa9HlOSdefqH8t7nxghhBBCCFnN',
                     'GwAA///sxbEJAAAIAzCh///sILj1g2TJnNiuAwC8BQAA//8DABVnAU2AFgAA'],
            'type': FileType.from_id(1).to_json(join=True),
            'observation': Observation.from_id(19).to_json(join=True)
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading file from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['file']):
            assert File.from_id(i + 1).to_json(join=False) == {**record, 'id': i + 1}

    def test_id_missing(self) -> None:
        """Test exception on missing file `id`."""
        with pytest.raises(NotFound):
            File.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on file `id` already exists."""
        with pytest.raises(IntegrityError):
            File.add({'id': 1, 'observation_id': 1, 'type_id': 1, 'data': b'...'})

    def test_from_observation(self, testdata: TestData) -> None:
        """Test loading file from `observation_id`."""
        for i, record in enumerate(testdata['file']):
            assert File.from_observation(record['observation_id']).to_json(join=False) == {**record, 'id': i + 1}

    def test_observation_missing(self) -> None:
        """Test exception on missing file `observation_id`."""
        with pytest.raises(NotFound):
            File.from_observation(-1)

    def test_observation_already_exists(self) -> None:
        """Test exception on file `observation` already exists."""
        with pytest.raises(IntegrityError):
            File.add({'observation_id': File.from_id(1).observation_id, 'type_id': 1, 'data': b'...'})

    def test_relationship_observation(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on file."""
        for i, record in enumerate(testdata['file']):
            assert File.from_id(i + 1).observation.id == record['observation_id']
