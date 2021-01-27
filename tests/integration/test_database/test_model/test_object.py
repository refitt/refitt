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

"""Database object model integration tests."""

# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Object, NotFound, AlreadyExists
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestObject:
    """Tests for `Object` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create object instance and validate accessors."""
        for data in testdata['object']:
            object = Object(**data)
            for key, value in data.items():
                assert getattr(object, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['object']:
            object = Object.from_dict(data)
            assert data == object.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['object']:
            object = Object.from_dict(data)
            assert tuple(data.values()) == object.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['object']:
            assert data == json_roundtrip(Object(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Object.from_id(1).to_json(join=True) == {
            'id': 1,
            'type_id': 1,
            'aliases': {'antares': 'ANT2020ae7t5xa', 'ztf': 'ZTF20actrfli', 'tag': 'determined_thirsty_cray'},
            'ra': 133.0164572,
            'dec': 44.80034109999999,
            'redshift': None,
            'data': {},
            'type': {
                'id': 1,
                'name': 'Unknown',
                'description': 'Objects with unknown or unspecified type'
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading object from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['object']):
            assert Object.from_id(i + 1).aliases == record['aliases']

    def test_id_missing(self) -> None:
        """Test exception on missing object `id`."""
        with pytest.raises(NotFound):
            Object.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on object `id` already exists."""
        with pytest.raises(IntegrityError):
            Object.add({'id': 1, 'type_id': 5,
                        'aliases': {'bayer': 'α Ori', 'flamsteed': '58 Ori', 'HR': 'HR 2061', 'BD': 'BD + 7°1055',
                                    'HD': 'HD 39801', 'FK5': 'FK5 224', 'HIP': 'HIP 27989', 'SAO': 'SAO 113271',
                                    'GC': 'GC 7451', 'CCDM': 'CCDM J05552+0724', 'AAVSO': 'AAVSO 0549+07'},
                        'ra': 88.7917, 'dec': 7.4069, 'redshift': 0.000073,
                        'data': {'parallax': 6.55, }})

    def test_from_alias(self, testdata: TestData) -> None:
        """Test loading object from known `alias`."""
        for record in testdata['object']:
            assert Object.from_alias(ztf=record['aliases']['ztf']).aliases == record['aliases']

    def test_alias_missing(self) -> None:
        """Test exception on object `alias` not found."""
        with pytest.raises(NotFound):
            Object.from_alias(foo='bar')

    def test_alias_exists(self) -> None:
        with pytest.raises(AlreadyExists):
            Object.add_alias(2, ztf=Object.from_id(1).aliases['ztf'])

    def test_relationship_object_type(self, testdata: TestData) -> None:
        """Test object foreign key relationship on object_type."""
        for i, record in enumerate(testdata['object']):
            assert Object.from_id(i + 1).type.id == record['type_id']
