# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Epoch, ModelType, Model, Observation, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestModel:
    """Tests for `Model` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create model instance and validate accessors."""
        for data in testdata['model']:
            model = Model(**data)
            for key, value in data.items():
                assert getattr(model, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['model']:
            model = Model.from_dict(data)
            assert data == model.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['model']:
            model = Model.from_dict(data)
            assert tuple(data.values()) == model.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['model']:
            assert data == json_roundtrip(Model(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        model = Model.from_id(1)
        assert model.to_json(join=True) == {
            'id': 1,
            'epoch_id': 1,
            'type_id': 1,
            'observation_id': model.observation_id,
            'data': model.data,
            'epoch': Epoch.from_id(1).to_json(join=True),
            'type': ModelType.from_id(1).to_json(join=True),
            'observation': Observation.from_id(model.observation_id).to_json(join=True)
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading model from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['model']):
            assert Model.from_id(i + 1).to_json(join=False) == {**record, 'id': i + 1}

    def test_id_missing(self) -> None:
        """Test exception on missing model `id`."""
        with pytest.raises(NotFound):
            Model.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on model `id` already exists."""
        with pytest.raises(IntegrityError):
            Model.add({'id': 1, 'epoch_id': 1, 'type_id': 1, 'observation_id': 1, 'data': {}})

    def test_relationship_epoch(self, testdata: TestData) -> None:
        """Test epoch foreign key relationship on model."""
        for i, record in enumerate(testdata['model']):
            assert Model.from_id(i + 1).epoch.id == record['epoch_id']

    def test_relationship_type(self, testdata: TestData) -> None:
        """Test type foreign key relationship on model."""
        for i, record in enumerate(testdata['model']):
            assert Model.from_id(i + 1).type.id == record['type_id']

    def test_relationship_observation(self, testdata: TestData) -> None:
        """Test observation foreign key relationship on model."""
        for i, record in enumerate(testdata['model']):
            assert Model.from_id(i + 1).observation.id == record['observation_id']
