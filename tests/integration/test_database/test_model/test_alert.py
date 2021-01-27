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

"""Database alert model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Alert, Observation, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestAlert:
    """Tests for `Alert` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create alert instance and validate accessors."""
        for data in testdata['alert']:
            alert = Alert(**data)
            for key, value in data.items():
                assert getattr(alert, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['alert']:
            alert = Alert.from_dict(data)
            assert data == alert.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['alert']:
            alert = Alert.from_dict(data)
            assert tuple(data.values()) == alert.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['alert']:
            assert data == json_roundtrip(Alert(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Alert.from_id(1).to_json(join=True) == {
            'id': 1,
            'observation_id': 1,
            'data': {
                'alert': {
                    'alert_id': 'ztf:...',
                    'dec': 44.80034109999999,
                    'mjd': 59146.916666666664,
                    'properties': {
                        'ztf_fid': 2,
                        'ztf_id': 'ZTF20actrfli',
                        'ztf_magpsf': 18.1,
                        'ztf_sigmapsf': 0.08
                    },
                    'ra': 133.0164572
                },
                'dec': 44.80034109999999,
                'locus_id': 'ANT2020ae7t5xa',
                'properties': {},
                'ra': 133.0164572
            },
            'observation': Observation.from_id(1).to_json(join=True)
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading alert from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['alert']):
            assert Alert.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing alert `id`."""
        with pytest.raises(NotFound):
            Alert.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on alert `id` already exists."""
        with pytest.raises(IntegrityError):
            Alert.add({'id': 1, 'observation_id': 11,  # NOTE: observation_id=11 is a forecast
                       'data': {}})

    def test_from_observation(self, testdata: TestData) -> None:
        """Test loading alert from `observation_id`."""
        for i, record in enumerate(testdata['alert']):
            assert Alert.from_observation(record['observation_id']).observation_id == record['observation_id']

    def test_observation_missing(self) -> None:
        """Test exception on missing alert `observation`."""
        with pytest.raises(NotFound):
            Alert.from_observation(-1)

    def test_observation_already_exists(self) -> None:
        """Test exception on alert `observation_id` already exists."""
        with pytest.raises(IntegrityError):
            Alert.add({'id': -1, 'observation_id': 1, 'data': {}})

    def test_relationship_observation_type(self, testdata: TestData) -> None:
        """Test alert foreign key relationship on observation."""
        for i, record in enumerate(testdata['alert']):
            assert Alert.from_id(i + 1).observation.id == record['observation_id']
