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

"""Database observation model integration tests."""


# standard libs
from datetime import datetime

# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import Observation, NotFound, Object, Source
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestObservation:
    """Tests for `Observation` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create observation instance and validate accessors."""
        for data in testdata['observation']:
            observation = Observation(**data)
            for key, value in data.items():
                assert getattr(observation, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['observation']:
            observation = Observation.from_dict(data)
            assert data == observation.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['observation']:
            observation = Observation.from_dict(data)
            assert tuple(data.values()) == observation.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['observation']:
            embedded_data = {**data, 'time': str(data['time']), 'recorded': str(data['recorded'])}
            assert embedded_data == json_roundtrip(Observation(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Observation.from_id(1).to_json(join=True) == {
            'id': 1,
            'time': '2020-10-24 18:00:00' + ('' if config.backend == 'sqlite' else '-04:00'),
            'object_id': 1,
            'type_id': 3,
            'source_id': 2,
            'value': 18.1,
            'error': 0.08,
            'recorded': '2020-10-24 18:01:00' + ('' if config.backend == 'sqlite' else '-04:00'),
            'object': {
                'id': 1,
                'type_id': 1,
                'aliases': {
                    'antares': 'ANT2020ae7t5xa',
                    'ztf': 'ZTF20actrfli',
                    'tag': 'determined_thirsty_cray',
                },
                'ra': 133.0164572,
                'dec': 44.80034109999999,
                'redshift': None,
                'data': {},
                'type': {
                    'id': 1,
                    'name': 'Unknown',
                    'description': 'Objects with unknown or unspecified type',
                },
            },
            'type': {
                'id': 3,
                'name': 'r-ztf',
                'units': 'mag',
                'description': 'R-band apparent magnitude (ZTF).'
            },
            'source': {
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
                },
            },
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading observation from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing observation `id`."""
        with pytest.raises(NotFound):
            Observation.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on observation `id` already exists."""
        with pytest.raises(IntegrityError):
            Observation.add({'id': 1, 'time': datetime.now(), 'object_id': 1, 'type_id': 1,
                             'source_id': 1, 'value': 3.14, 'error': None})

    def test_relationship_observation_type(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on observation_type."""
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).type.id == record['type_id']

    def test_relationship_object(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on object."""
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).object.id == record['object_id']

    def test_relationship_source(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on source."""
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).source.id == record['source_id']

    def test_relationship_object_type(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on object -> object_type."""
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).object.type.id == Object.from_id(record['object_id']).type.id

    def test_relationship_source_type(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on source -> source_type."""
        for i, record in enumerate(testdata['observation']):
            assert Observation.from_id(i + 1).source.type.id == Source.from_id(record['source_id']).type.id

    def test_with_object(self) -> None:
        """Test query for observations for a given object."""
        for object_id, count in [(1, 9), (10, 3)]:
            results = Observation.with_object(object_id)
            assert all(isinstance(obs, Observation) for obs in results)
            assert len(results) == count

    def test_with_source(self) -> None:
        """Test query for observations for a given source."""
        for source_id in [3, 4, 5, 6]:
            results = Observation.with_source(source_id)
            assert all(isinstance(obs, Observation) for obs in results)
            assert len(results) == 6
