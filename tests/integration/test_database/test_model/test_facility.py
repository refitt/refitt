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

"""Database facility model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import Facility, NotFound, User, FacilityMap
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestFacility:
    """Tests for `Facility` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create facility instance and validate accessors."""
        for data in testdata['facility']:
            facility = Facility(**data)
            for key, value in data.items():
                assert getattr(facility, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['facility']:
            facility = Facility.from_dict(data)
            assert data == facility.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['facility']:
            facility = Facility.from_dict(data)
            assert tuple(data.values()) == facility.to_tuple()

    def test_embedded(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['facility']:
            assert data == json_roundtrip(Facility(**data).to_json())

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading facility profile from `id`."""
        # NOTE: `id` not set until after insert
        for i, facility in enumerate(testdata['facility']):
            assert Facility.from_id(i + 1).name == facility['name']

    def test_from_id_missing(self) -> None:
        """Test exception on missing facility `id`."""
        with pytest.raises(NotFound):
            Facility.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on facility `id` already exists."""
        with pytest.raises(IntegrityError):
            Facility.add({'id': 1, 'name': 'Wayne_4m', 'latitude': -24.5, 'longitude': -69.25, 'elevation': 5050,
                          'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading facility profile from `name`."""
        for facility in testdata['facility']:
            assert Facility.from_name(facility['name']).name == facility['name']

    def test_from_name_missing(self) -> None:
        """Test exception on missing facility `name`."""
        with pytest.raises(NotFound):
            Facility.from_name('Wayne_18in')

    def test_name_already_exists(self) -> None:
        """Test exception on facility `name` already exists."""
        with pytest.raises(IntegrityError):
            Facility.add({'name': 'Croft_4m', 'latitude': -24.5, 'longitude': -69.25, 'elevation': 5050,
                          'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})

    def test_update_limiting_magnitude(self) -> None:
        """Update limiting magnitude of facility profile."""
        old_lmag, new_lmag = 15.5, 15.4
        assert Facility.from_id(1).name == 'Bourne_12in'
        assert Facility.from_name('Bourne_12in').limiting_magnitude == old_lmag
        Facility.update(1, limiting_magnitude=new_lmag)
        assert Facility.from_name('Bourne_12in').limiting_magnitude == new_lmag
        Facility.update(1, limiting_magnitude=old_lmag)
        assert Facility.from_name('Bourne_12in').limiting_magnitude == old_lmag

    def test_update_data(self) -> None:
        """Update custom data of facility profile."""
        old_data = {'telescope_design': 'reflector'}
        new_data = {'telescope_design': 'reflector', 'special_field': 42}
        assert Facility.from_id(2).name == 'Croft_1m'
        assert Facility.from_name('Croft_1m').data == old_data
        Facility.update(2, special_field=42)
        assert Facility.from_name('Croft_1m').data == new_data
        Facility.update(2, data=old_data)
        assert Facility.from_name('Croft_1m').data == old_data

    def test_users(self) -> None:
        """Access associated facility users."""
        users = Facility.from_name('Croft_4m').users()
        assert all(isinstance(user, User) for user in users)
        assert len(users) == 1

    def test_add_user(self) -> None:
        """Test adding a user and then removing it."""
        facility = Facility.from_name('Croft_4m')
        users = facility.users()
        assert len(users) == 1 and users[0].alias == 'tomb_raider'
        User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                  'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        new_user = User.from_alias('007')
        facility.add_user(new_user.id)
        users = facility.users()
        assert len(users) == 2 and set(u.alias for u in users) == {'tomb_raider', '007'}
        User.delete(new_user.id)
        users = facility.users()
        assert len(users) == 1 and users[0].alias == 'tomb_raider'

    def test_delete(self) -> None:
        """Add a new facility record and then delete it."""
        assert Facility.count() == 4
        Facility.add({'name': 'Croft_10m', 'latitude': -24.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 20.5})
        assert Facility.count() == 5
        assert Facility.from_name('Croft_10m').limiting_magnitude == 20.5
        Facility.delete(Facility.from_name('Croft_10m').id)
        assert Facility.count() == 4

    def test_delete_missing(self) -> None:
        """Test exception on attempt to delete non-existent facility."""
        with pytest.raises(NotFound):
            Facility.delete(-1)

    def test_delete_facility_map_cascade(self) -> None:
        """Create a new facility, associate it with a user, then remove."""
        assert User.count() == 4 and Facility.count() == 4 and FacilityMap.count() == 4
        Facility.add({'name': 'Bourne_4m', 'latitude': -24.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})
        facility = Facility.from_name('Bourne_4m')
        user = User.from_alias('delta_one')
        user.add_facility(facility.id)
        assert User.count() == 4 and Facility.count() == 5 and FacilityMap.count() == 5
        Facility.delete(facility.id)
        assert User.count() == 4 and Facility.count() == 4 and FacilityMap.count() == 4
