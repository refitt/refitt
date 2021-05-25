# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database forecast model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Forecast, Observation, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestForecast:
    """Tests for `Forecast` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create forecast instance and validate accessors."""
        for data in testdata['forecast']:
            forecast = Forecast(**data)
            for key, value in data.items():
                assert getattr(forecast, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['forecast']:
            forecast = Forecast.from_dict(data)
            assert data == forecast.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['forecast']:
            forecast = Forecast.from_dict(data)
            assert tuple(data.values()) == forecast.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['forecast']:
            assert data == json_roundtrip(Forecast(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        forecast = Forecast.from_id(1)
        assert forecast.to_json(join=True) == {
            'id': 1,
            'observation_id': forecast.observation_id,
            'data': forecast.data,
            'observation': Observation.from_id(forecast.observation_id).to_json(join=True)
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading forecast from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['forecast']):
            assert Forecast.from_id(i + 1).to_json(join=False) == {**record, 'id': i + 1}

    def test_id_missing(self) -> None:
        """Test exception on missing forecast `id`."""
        with pytest.raises(NotFound):
            Forecast.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on forecast `id` already exists."""
        with pytest.raises(IntegrityError):
            Forecast.add({'id': 1, 'observation_id': 1, 'data': {}})

    def test_from_observation(self, testdata: TestData) -> None:
        """Test loading forecast from `observation_id`."""
        for i, record in enumerate(testdata['forecast']):
            assert Forecast.from_observation(record['observation_id']).to_json(join=False) == {**record, 'id': i + 1}

    def test_observation_missing(self) -> None:
        """Test exception on missing forecast `observation_id`."""
        with pytest.raises(NotFound):
            Forecast.from_observation(-1)

    def test_observation_already_exists(self) -> None:
        """Test exception on forecast `observation` already exists."""
        with pytest.raises(IntegrityError):
            Forecast.add({'observation_id': Forecast.from_id(1).observation_id, 'data': {}})

    def test_relationship_observation(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on forecast."""
        for i, record in enumerate(testdata['forecast']):
            assert Forecast.from_id(i + 1).observation.id == record['observation_id']
