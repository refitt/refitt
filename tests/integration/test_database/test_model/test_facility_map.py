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
