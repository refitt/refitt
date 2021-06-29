# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database facility_map model integration tests."""


# internal libs
from refitt.database.model import FacilityMap
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestFacilityMap:
    """Tests for `FacilityMap` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create facility_map instance and validate accessors."""
        for data in testdata['facility_map']:
            facility_map = FacilityMap(**data)
            for key, value in data.items():
                assert getattr(facility_map, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['facility_map']:
            facility_map = FacilityMap.from_dict(data)
            assert data == facility_map.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['facility_map']:
            facility_map = FacilityMap.from_dict(data)
            assert tuple(data.values()) == facility_map.to_tuple()

    def test_embedded(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['facility_map']:
            assert data == json_roundtrip(FacilityMap(**data).to_json())
