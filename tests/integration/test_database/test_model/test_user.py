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

"""Database user model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.model import User, NotFound, Facility, FacilityMap
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


class TestUser:
    """Tests for `User` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create user instance and validate accessors."""
        for data in testdata['user']:
            user = User(**data)
            for key, value in data.items():
                assert getattr(user, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['user']:
            user = User.from_dict(data)
            assert data == user.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['user']:
            user = User.from_dict(data)
            assert tuple(data.values()) == user.to_tuple()

    def test_embedded(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['user']:
            assert data == json_roundtrip(User(**data).to_json())

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading user profile from `id`."""
        # NOTE: `id` not set until after insert
        for i, user in enumerate(testdata['user']):
            assert User.from_id(i + 1).alias == user['alias']

    def test_from_id_missing(self) -> None:
        """Test exception on missing user `id`."""
        with pytest.raises(NotFound):
            User.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on user `id` already exists."""
        with pytest.raises(IntegrityError):
            User.add({'id': 1, 'first_name': 'Bruce', 'last_name': 'Wayne', 'email': 'bruce@waynecorp.com',
                      'alias': 'batman', 'data': {'user_type': 'amateur'}})

    def test_from_email(self, testdata: TestData) -> None:
        """Test loading user profile from `email`."""
        for user in testdata['user']:
            assert User.from_email(user['email']).email == user['email']

    def test_from_email_missing(self) -> None:
        """Test exception on missing user `email`."""
        with pytest.raises(NotFound):
            User.from_email('batman@justiceleague.org')

    def test_email_already_exists(self) -> None:
        """Test exception on user `email` already exists."""
        with pytest.raises(IntegrityError):
            User.add({'first_name': 'Bruce', 'last_name': 'Wayne', 'email': 'bourne@cia.gov',
                      'alias': 'batman', 'data': {'user_type': 'amateur'}})

    def test_from_alias(self, testdata: TestData) -> None:
        """Test loading user profile from `alias`."""
        for user in testdata['user']:
            assert User.from_alias(user['alias']).alias == user['alias']

    def test_from_alias_missing(self) -> None:
        """Test exception on missing user `alias`."""
        with pytest.raises(NotFound):
            User.from_alias('batman')

    def test_alias_already_exists(self) -> None:
        """Test exception on user `alias` already exists."""
        with pytest.raises(IntegrityError):
            User.add({'first_name': 'Bryce', 'last_name': 'Wayne', 'email': 'bruce@waynecorp.com',
                      'alias': 'tomb_raider', 'data': {'user_type': 'amateur'}})

    def test_update_email(self) -> None:
        """Update email address of user profile."""
        old_email, new_email = 'bourne@cia.gov', 'jason.bourne@cia.gov'
        user = User.from_alias('delta_one')
        assert user.email == old_email
        User.update(user.id, email=new_email)
        assert User.from_alias('delta_one').email == User.from_email(new_email).email
        User.update(user.id, email=old_email)
        assert User.from_alias('delta_one').email == User.from_email(old_email).email

    def test_update_data(self) -> None:
        """Update custom data of user profile."""
        old_data = {'user_type': 'amateur'}
        new_data = {'user_type': 'amateur', 'special_field': 42}
        user_id = User.from_alias('tomb_raider').id
        assert User.from_id(user_id).data == old_data
        User.update(user_id, special_field=42)
        assert User.from_id(user_id).data == new_data
        User.update(user_id, data=old_data)
        assert User.from_id(user_id).data == old_data

    def test_facilities(self) -> None:
        """Access associated user facilities."""
        facilities = User.from_alias('tomb_raider').facilities()
        assert all(isinstance(facility, Facility) for facility in facilities)
        assert len(facilities) == 2

    def test_add_facility(self) -> None:
        """Test adding a facility and then removing it."""
        user = User.from_alias('tomb_raider')
        facilities = user.facilities()
        assert len(facilities) == 2 and set(f.name for f in facilities) == {'Croft_1m', 'Croft_4m'}
        Facility.add({'name': 'Croft_10m', 'latitude': -25.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 20.5})
        new_facility = Facility.from_name('Croft_10m')
        user.add_facility(new_facility.id)
        facilities = user.facilities()
        assert len(facilities) == 3 and set(f.name for f in facilities) == {'Croft_1m', 'Croft_4m', 'Croft_10m'}
        user.delete_facility(new_facility.id)
        Facility.delete(new_facility.id)
        facilities = user.facilities()
        assert len(facilities) == 2 and set(f.name for f in facilities) == {'Croft_1m', 'Croft_4m'}

    def test_delete(self) -> None:
        """Add a new user record and then remove it."""
        assert User.count() == 4
        User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                  'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5
        assert User.from_alias('007').last_name == 'Bond'
        User.delete(User.from_alias('007').id)
        assert User.count() == 4

    def test_delete_missing(self) -> None:
        """Test exception on attempt to delete non-existent user."""
        with pytest.raises(NotFound):
            User.delete(-1)

    def test_delete_facility_map_cascade(self) -> None:
        """Create a new user, with facility, then remove."""
        assert User.count() == 4 and Facility.count() == 4 and FacilityMap.count() == 4
        User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                  'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        user = User.from_alias('007')
        Facility.add({'name': 'Bond_4m', 'latitude': -25.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})
        facility = Facility.from_name('Bond_4m')
        user.add_facility(facility.id)
        assert user.facilities()[0].to_dict() == facility.to_dict()
        assert User.count() == 5 and Facility.count() == 5 and FacilityMap.count() == 5
        User.delete(user.id)
        assert User.count() == 4 and Facility.count() == 5 and FacilityMap.count() == 4
        Facility.delete(facility.id)
        assert Facility.count() == 4
