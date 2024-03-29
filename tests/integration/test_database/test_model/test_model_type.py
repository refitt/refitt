# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database model_type model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import ModelType, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestModelType:
    """Tests for `ModelType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create model_type instance and validate accessors."""
        for data in testdata['model_type']:
            model_type = ModelType(**data)
            for key, value in data.items():
                assert getattr(model_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['model_type']:
            model_type = ModelType.from_dict(data)
            assert data == model_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['model_type']:
            model_type = ModelType.from_dict(data)
            assert tuple(data.values()) == model_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['model_type']:
            assert data == json_roundtrip(ModelType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert ModelType.from_name('conv_auto_encoder').to_json(join=True) == {
            'id': 1,
            'name': 'conv_auto_encoder',
            'description': 'Original forecast model used by REFITT.'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading model_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['model_type']):
            assert ModelType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing model_type `id`."""
        with pytest.raises(NotFound):
            ModelType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on model_type `id` already exists."""
        with pytest.raises(IntegrityError):
            ModelType.add({'id': 1, 'name': 'other_model_type_name',
                          'description': 'Another amazing model type.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading model_type from `name`."""
        for record in testdata['model_type']:
            assert ModelType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing model_type `name`."""
        with pytest.raises(NotFound):
            ModelType.from_name('other')

    def test_name_already_exists(self) -> None:
        """Test exception on model_type `name` already exists."""
        with pytest.raises(IntegrityError):
            ModelType.add({'name': 'conv_auto_encoder',
                           'description': 'A different sort of forecast'})
