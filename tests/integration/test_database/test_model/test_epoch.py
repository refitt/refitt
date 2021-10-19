# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database epoch model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import Epoch, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestEpoch:
    """Tests for `Epoch` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create epoch instance and validate accessors."""
        for data in testdata['epoch']:
            epoch = Epoch(**data)
            for key, value in data.items():
                assert getattr(epoch, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['epoch']:
            epoch = Epoch.from_dict(data)
            assert data == epoch.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['epoch']:
            epoch = Epoch.from_dict(data)
            assert tuple(data.values()) == epoch.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['epoch']:
            assert data == json_roundtrip(Epoch(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert Epoch.from_id(1).to_json(join=True) == {
            'id': 1,
            'created': '2020-10-24 20:01:00' + ('' if config.provider == 'sqlite' else '-04:00')
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading epoch from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['epoch']):
            assert Epoch.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing epoch `id`."""
        with pytest.raises(NotFound):
            Epoch.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on epoch `id` already exists."""
        with pytest.raises(IntegrityError):
            Epoch.add({'id': 1})

    def test_new(self) -> None:
        """Test the creation of a new epoch."""
        assert Epoch.count() == 4
        epoch = Epoch.new()
        assert Epoch.count() == 5
        Epoch.delete(epoch.id)
        assert Epoch.count() == 4

    def test_latest(self) -> None:
        """Test query for latest epoch."""
        assert Epoch.latest().to_json(join=True) == {
            'id': 4,
            'created': '2020-10-27 20:01:00' + ('' if config.provider == 'sqlite' else '-04:00')
        }

    def test_select_with_limit(self) -> None:
        """Test the selection of epoch with a limit."""
        assert [group.to_json(join=True) for group in Epoch.select(limit=2)] == [
            {'id': 4, 'created': '2020-10-27 20:01:00-04:00'},
            {'id': 3, 'created': '2020-10-26 20:01:00-04:00'}
        ]

    def test_select_with_limit_and_offset(self) -> None:
        """Test the selection of epoch with a limit and offset."""
        assert [group.to_json(join=True) for group in Epoch.select(limit=2, offset=2)] == [
            {
                'id': 2,
                'created': '2020-10-25 20:01:00' + ('' if config.provider == 'sqlite' else '-04:00')
            },
            {
                'id': 1,
                'created': '2020-10-24 20:01:00' + ('' if config.provider == 'sqlite' else '-04:00')
            }
        ]
