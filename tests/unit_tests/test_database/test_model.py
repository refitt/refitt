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

"""Tests for Refitt's database model."""


# type annotations
from typing import List, Dict, Any

# standard libs
import json
from datetime import datetime

# external libs
import pytest
from names_generator import generate_name
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database.core import config
from refitt.web.token import JWT
from refitt.database.model import (User, Facility, FacilityMap, Client, Session,
                                   ObjectType, Object, SourceType, Source, ObservationType, Observation,
                                   Alert, FileType, File, Forecast,
                                   RecommendationGroup, Recommendation, ModelType, Model, NotFound, AlreadyExists)


# test data fixture return type
Record = Dict[str, Any]
Records = List[Record]
TestData = Dict[str, Records]


def serializable(data: dict) -> dict:
    """Input `data` is returned after JSON round trip."""
    return json.loads(json.dumps(data))


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
            assert data == serializable(User(**data).to_json())

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
            assert data == serializable(Facility(**data).to_json())

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
            assert data == serializable(FacilityMap(**data).to_json())


class TestClient:
    """Tests for `Client` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create client instance and validate accessors."""
        for data in testdata['client']:
            client = Client(**data)
            for key, value in data.items():
                assert getattr(client, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['client']:
            client = Client.from_dict(data)
            assert data == client.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['client']:
            client = Client.from_dict(data)
            assert tuple(data.values()) == client.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['client']:
            embedded_data = {**data, 'created': str(data['created'])}
            assert embedded_data == serializable(Client(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Client.from_user(User.from_alias('delta_one').id).to_json(join=True) == {
            'id': 2,
            'user_id': 2,
            'level': 10,
            'key': '78h6IuhW30Re7I-C',
            'secret': '7ccb08b171f4a28e6b5f2af5597153873d7cd90a972f2bee7b8ac82c43e0e4e9',
            'valid': True,
            'created': '2020-10-23 17:45:01' + ('' if config.backend == 'sqlite' else '-04:00'),
            'user': {
                'id': 2,
                'first_name': 'Jason',
                'last_name': 'Bourne',
                'email': 'bourne@cia.gov',
                'alias': 'delta_one',
                'data': {
                    'user_type': 'amateur'
                }
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading client from `id`."""
        # NOTE: `id` not set until after insert
        for i, client in enumerate(testdata['client']):
            assert Client.from_id(i + 1).user.alias == testdata['user'][i]['alias']

    def test_id_missing(self) -> None:
        """Test exception on missing client `id`."""
        with pytest.raises(NotFound):
            Client.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on client `id` already exists."""
        with pytest.raises(IntegrityError):
            Client.add({'id': 1, 'user_id': 1, 'level': 10, 'key': 'abc...', 'secret': 'abc...', 'valid': True})

    def test_from_user(self) -> None:
        """Test loading client from `user`."""
        for id in range(1, 4):
            assert id == Client.from_user(id).user_id == User.from_id(id).id

    def test_user_missing(self) -> None:
        """Test exception on missing client `user_id`."""
        with pytest.raises(NotFound):
            Client.from_user(-1)

    def test_user_already_exists(self) -> None:
        """Test exception on client `user` already exists."""
        with pytest.raises(IntegrityError):
            Client.add({'user_id': 1, 'level': 10, 'key': 'abc...', 'secret': 'abc...', 'valid': True})

    def test_from_key(self, testdata: TestData) -> None:
        """Test loading client from `key`."""
        for client in testdata['client']:
            assert Client.from_key(client['key']).key == client['key']

    def test_key_missing(self) -> None:
        """Test exception on missing client `key`."""
        with pytest.raises(NotFound):
            Client.from_key('abc...')

    def test_key_already_exists(self) -> None:
        """Test exception on client `key` already exists."""
        with pytest.raises(IntegrityError):
            client_1 = Client.from_id(1)
            client_2 = Client.from_id(2)
            Client.update(client_1.id, key=client_2.key)

    def test_relationship_user(self) -> None:
        """Test user foreign key relationship."""
        for id in range(1, 4):
            assert id == Client.from_user(id).user.id == User.from_id(id).id

    def test_delete(self) -> None:
        """Add a new user and client. Remove the client directly."""
        assert User.count() == 4 and Client.count() == 4
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4
        key, secret, client = Client.new(user_id)
        assert User.count() == 5 and Client.count() == 5
        Client.delete(client.id)
        assert User.count() == 5 and Client.count() == 4
        User.delete(user_id)
        assert User.count() == 4 and Client.count() == 4

    def test_delete_user_cascade(self) -> None:
        """Add a new user and client record and then remove them."""
        assert User.count() == 4 and Client.count() == 4
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4
        Client.new(user_id)
        assert User.count() == 5 and Client.count() == 5
        User.delete(user_id)
        assert User.count() == 4 and Client.count() == 4

    def test_new_secret(self) -> None:
        """Generate a new client secret and then manually reset it back."""
        user = User.from_alias('tomb_raider')
        old_hash = Client.from_user(user.id).secret
        key, secret = Client.new_secret(user.id)
        new_hash = secret.hashed().value
        assert new_hash != old_hash
        Client.update(Client.from_user(user.id).id, secret=old_hash)
        assert Client.from_user(user.id).secret == old_hash

    def test_new_key_and_secret(self) -> None:
        """Generate a new client key and secret and then manually reset them."""
        user = User.from_alias('tomb_raider')
        data = Client.from_user(user.id).to_dict()
        old_key, old_secret_hash = data['key'], data['secret']
        key, secret = Client.new_key(user.id)
        assert key.value != old_key and secret.hashed().value != old_secret_hash
        Client.update(Client.from_key(key.value).id, key=old_key, secret=old_secret_hash)
        client = Client.from_user(user.id)
        assert client.key == old_key and client.secret == old_secret_hash


class TestSession:
    """Tests for `Session` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create session instance and validate accessors."""
        for data in testdata['session']:
            session = Session(**data)
            for key, value in data.items():
                assert getattr(session, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['session']:
            session = Session.from_dict(data)
            assert data == session.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['client']:
            client = Client.from_dict(data)
            assert tuple(data.values()) == client.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['session']:
            embedded_data = {**data, 'expires': str(data['expires']), 'created': str(data['created'])}
            assert embedded_data == serializable(Session(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Session.from_id(2).to_json(join=True) == {
            'id': 2,
            'client_id': 2,
            'expires': '2020-10-23 18:00:01' + ('' if config.backend == 'sqlite' else '-04:00'),
            'token': 'c44d20d18e734aea40b30682a57162b53c18f676c1b752696dad5dc6586187fe',
            'created': '2020-10-23 17:45:01' + ('' if config.backend == 'sqlite' else '-04:00'),
            'client': {'id': 2,
                       'user_id': 2,
                       'level': 10,
                       'key': '78h6IuhW30Re7I-C',
                       'secret': '7ccb08b171f4a28e6b5f2af5597153873d7cd90a972f2bee7b8ac82c43e0e4e9',
                       'valid': True,
                       'created': '2020-10-23 17:45:01' + ('' if config.backend == 'sqlite' else '-04:00'),
                       'user': {'id': 2,
                                'first_name': 'Jason',
                                'last_name': 'Bourne',
                                'email': 'bourne@cia.gov',
                                'alias': 'delta_one',
                                'data': {
                                    'user_type': 'amateur'}
                                }
                       }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading session from `id`."""
        # NOTE: `id` not set until after insert
        for id in range(1, 4):
            assert Session.from_id(id).client.user.alias == testdata['user'][id-1]['alias']

    def test_id_missing(self) -> None:
        """Test exception on missing session `id`."""
        with pytest.raises(NotFound):
            Session.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on session `id` already exists."""
        with pytest.raises(IntegrityError):
            Session.add({'id': 1, 'client_id': 1, 'expires': datetime.now(), 'token': 'abc...'})

    def test_from_client(self) -> None:
        """Test loading session from `client`."""
        for id in range(1, 4):
            assert id == Session.from_client(id).client_id == Client.from_id(id).id

    def test_client_missing(self) -> None:
        """Test exception on missing session `client`."""
        with pytest.raises(NotFound):
            Session.from_client(-1)

    def test_client_already_exists(self) -> None:
        """Test exception on session `client` already exists."""
        with pytest.raises(IntegrityError):
            Session.add({'client_id': 1, 'expires': datetime.now(), 'token': 'abc...'})

    def test_relationship_client(self) -> None:
        """Test session foreign key relationship."""
        for id in range(1, 4):
            assert id == Session.from_client(id).client.id == Client.from_id(id).id

    def test_delete(self) -> None:
        """Add a new session and remove it directly."""
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4 and Session.count() == 4
        key, secret, client = Client.new(user_id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        Session.new(user_id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 5
        Session.delete(Session.from_client(client.id).id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        User.delete(user_id)  # NOTE: deletes client
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4

    def test_delete_client_cascade(self) -> None:
        """Add a new user, client, and session. Remove user to clear client and session."""
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4 and Session.count() == 4
        Client.new(user_id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        Session.new(user_id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 5
        User.delete(user_id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4

    def test_new_token(self) -> None:
        """Generate a new session token and then manually reset it back."""
        session = Session.from_client(2)
        before = session.created
        if config.backend == 'sqlite':
            assert datetime.now() > before
        else:
            assert datetime.now().astimezone() > before
        old_hash = session.token
        expired = session.expires
        jwt = Session.new(2)
        assert isinstance(jwt, JWT)
        assert jwt.exp > datetime.now()
        new_session = Session.from_client(2)
        assert new_session.created > before
        assert new_session.token != old_hash and len(new_session.token) == len(old_hash)
        Session.update(2, token=old_hash, created=before, expires=expired)  # NOTE: hard reset
        new_session = Session.from_client(2)
        assert new_session.created == before
        assert new_session.token == old_hash
        assert new_session.expires == expired


class TestObjectType:
    """Tests for `ObjectType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create object_type instance and validate accessors."""
        for data in testdata['object_type']:
            object_type = ObjectType(**data)
            for key, value in data.items():
                assert getattr(object_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['object_type']:
            object_type = ObjectType.from_dict(data)
            assert data == object_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['object_type']:
            object_type = ObjectType.from_dict(data)
            assert tuple(data.values()) == object_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['object_type']:
            assert data == json.loads(json.dumps(ObjectType(**data).to_json(join=False)))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert ObjectType.from_name('SNIa').to_json(join=True) == {
            'id': 2,
            'name': 'SNIa',
            'description': 'WD detonation, Type Ia SN'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading object_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['object_type']):
            assert ObjectType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing object_type `id`."""
        with pytest.raises(NotFound):
            ObjectType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on object_type `id` already exists."""
        with pytest.raises(IntegrityError):
            ObjectType.add({'id': 1, 'name': 'Ludicrous Nova', 'description': 'The biggest ever'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading object_type from `name`."""
        for record in testdata['object_type']:
            assert ObjectType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing object_type `name`."""
        with pytest.raises(NotFound):
            ObjectType.from_name('Ludicrous SN')

    def test_name_already_exists(self) -> None:
        """Test exception on object_type `name` already exists."""
        with pytest.raises(IntegrityError):
            ObjectType.add({'name': 'SNIa', 'description': 'WD detonation, Type Ia SN'})


class TestObject:
    """Tests for `Object` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create object instance and validate accessors."""
        for data in testdata['object']:
            object = Object(**data)
            for key, value in data.items():
                assert getattr(object, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['object']:
            object = Object.from_dict(data)
            assert data == object.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['object']:
            object = Object.from_dict(data)
            assert tuple(data.values()) == object.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['object']:
            assert data == serializable(Object(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Object.from_name('competent_mayer').to_json(join=True) == {
            'id': 1,
            'type_id': 1,
            'name': 'competent_mayer',
            'aliases': {'antares': 'ANT2020ae7t5xa', 'ztf': 'ZTF20actrfli', 'refitt': 'competent_mayer'},
            'ra': 133.0164572,
            'dec': 44.80034109999999,
            'redshift': None,
            'data': {},
            'type': {
                'id': 1,
                'name': 'Unknown',
                'description': 'Objects with unknown or unspecified type'
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading object from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['object']):
            assert Object.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing object `id`."""
        with pytest.raises(NotFound):
            Object.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on object `id` already exists."""
        with pytest.raises(IntegrityError):
            Object.add({'id': 1, 'type_id': 5, 'name': 'Betelgeuse',
                        'aliases': {'bayer': 'α Ori', 'flamsteed': '58 Ori', 'HR': 'HR 2061', 'BD': 'BD + 7°1055',
                                    'HD': 'HD 39801', 'FK5': 'FK5 224', 'HIP': 'HIP 27989', 'SAO': 'SAO 113271',
                                    'GC': 'GC 7451', 'CCDM': 'CCDM J05552+0724', 'AAVSO': 'AAVSO 0549+07'},
                        'ra': 88.7917, 'dec': 7.4069, 'redshift': 0.000073,
                        'data': {'parallax': 6.55, }})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading object from `name`."""
        for record in testdata['object']:
            assert Object.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing object `name`."""
        with pytest.raises(NotFound):
            Object.from_name('Missing Object Name')

    def test_name_already_exists(self) -> None:
        """Test exception on object `name` already exists."""
        with pytest.raises(IntegrityError):
            Object.add({'type_id': 1, 'name': 'competent_mayer',
                        'aliases': {'ztf': 'ZTF20actrfli', 'antares': 'ANT2020ae7t5xa'},
                        'ra': 133.0164572, 'dec': 44.80034109999999, 'redshift': None, 'data': {}})

    def test_from_alias(self, testdata: TestData) -> None:
        """Test loading object from known `alias`."""
        for record in testdata['object']:
            assert Object.from_alias(ztf=record['aliases']['ztf']).name == record['name']

    def test_alias_missing(self) -> None:
        """Test exception on object `alias` not found."""
        with pytest.raises(NotFound):
            Object.from_alias(foo='bar')

    def test_alias_exists(self) -> None:
        with pytest.raises(AlreadyExists):
            Object.add_alias(2, ztf=Object.from_id(1).aliases['ztf'])

    def test_relationship_object_type(self, testdata: TestData) -> None:
        """Test object foreign key relationship on object_type."""
        for i, record in enumerate(testdata['object']):
            assert Object.from_id(i + 1).type.id == record['type_id']


class TestObservationType:
    """Tests for `ObservationType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create observation_type instance and validate accessors."""
        for data in testdata['observation_type']:
            observation_type = ObservationType(**data)
            for key, value in data.items():
                assert getattr(observation_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['observation_type']:
            observation_type = ObservationType.from_dict(data)
            assert data == observation_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['observation_type']:
            observation_type = ObservationType.from_dict(data)
            assert tuple(data.values()) == observation_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['observation_type']:
            assert data == serializable(ObservationType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert ObservationType.from_name('g-ztf').to_json(join=True) == {
            'id': 2,
            'name': 'g-ztf',
            'units': 'mag',
            'description': 'G-band apparent magnitude (ZTF).'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading observation_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['observation_type']):
            assert ObservationType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing observation_type `id`."""
        with pytest.raises(NotFound):
            ObservationType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on observation_type `id` already exists."""
        with pytest.raises(IntegrityError):
            ObservationType.add({'id': 1, 'name': 'New Type', 'units': 'Kilo-Frobnicate',
                                 'description': 'A new filter type.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading observation_type from `name`."""
        for record in testdata['observation_type']:
            assert ObservationType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing observation_type `name`."""
        with pytest.raises(NotFound):
            ObservationType.from_name('Missing ObservationType Name')

    def test_name_already_exists(self) -> None:
        """Test exception on observation_type `name` already exists."""
        with pytest.raises(IntegrityError):
            ObservationType.add({'name': 'clear', 'units': 'mag',
                                 'description': 'Un-filtered apparent magnitude.'})


class TestSourceType:
    """Tests for `SourceType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create source_type instance and validate accessors."""
        for data in testdata['source_type']:
            source_type = SourceType(**data)
            for key, value in data.items():
                assert getattr(source_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['source_type']:
            source_type = SourceType.from_dict(data)
            assert data == source_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['source_type']:
            source_type = SourceType.from_dict(data)
            assert tuple(data.values()) == source_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['source_type']:
            assert data == serializable(SourceType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert SourceType.from_name('catalog').to_json(join=True) == {
            'id': 2,
            'name': 'catalog',
            'description': 'Real observations from external catalogs.'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading source_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['source_type']):
            assert SourceType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing source_type `id`."""
        with pytest.raises(NotFound):
            SourceType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on source_type `id` already exists."""
        with pytest.raises(IntegrityError):
            SourceType.add({'id': 2, 'name': 'other catalog',
                            'description': 'Real observations from external catalogs.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading source_type from `name`."""
        for record in testdata['source_type']:
            assert SourceType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing source_type `name`."""
        with pytest.raises(NotFound):
            SourceType.from_name('Missing SourceType Name')

    def test_name_already_exists(self) -> None:
        """Test exception on source_type `name` already exists."""
        with pytest.raises(IntegrityError):
            SourceType.add({'name': 'catalog',
                            'description': 'Real observations from external catalogs.'})


class TestSource:
    """Tests for `Source` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create source instance and validate accessors."""
        for data in testdata['source']:
            source = Source(**data)
            for key, value in data.items():
                assert getattr(source, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['source']:
            source = Source.from_dict(data)
            assert data == source.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['source']:
            source = Source.from_dict(data)
            assert tuple(data.values()) == source.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['source']:
            assert data == serializable(Source(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Source.from_name('antares').to_json(join=True) == {
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
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading source from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['source']):
            assert Source.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing source `id`."""
        with pytest.raises(NotFound):
            Source.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on source `id` already exists."""
        with pytest.raises(IntegrityError):
            Source.add({'id': 1, 'type_id': 1, 'facility_id': None, 'user_id': None,
                        'name': 'other', 'description': '...', 'data': {}})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading source from `name`."""
        for record in testdata['source']:
            assert Source.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing source `name`."""
        with pytest.raises(NotFound):
            Source.from_name('Missing Source Name')

    def test_name_already_exists(self) -> None:
        """Test exception on source `name` already exists."""
        with pytest.raises(IntegrityError):
            Source.add({'type_id': 1, 'facility_id': None, 'user_id': 1, 'name': 'refitt',
                        'description': '...', 'data': {}})

    def test_relationship_source_type(self, testdata: TestData) -> None:
        """Test source foreign key relationship on source_type."""
        for i, record in enumerate(testdata['source']):
            assert Source.from_id(i + 1).type.id == record['type_id']


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
            assert embedded_data == serializable(Observation(**data).to_json(join=False))

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
                'name': 'competent_mayer',
                'aliases': {
                    'antares': 'ANT2020ae7t5xa',
                    'ztf': 'ZTF20actrfli',
                    'refitt': 'competent_mayer',
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
            assert data == serializable(Alert(**data).to_json(join=False))

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


class TestFileType:
    """Tests for `FileType` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create file_type instance and validate accessors."""
        for data in testdata['file_type']:
            file_type = FileType(**data)
            for key, value in data.items():
                assert getattr(file_type, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['file_type']:
            file_type = FileType.from_dict(data)
            assert data == file_type.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['file_type']:
            file_type = FileType.from_dict(data)
            assert tuple(data.values()) == file_type.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['file_type']:
            assert data == serializable(FileType(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert FileType.from_name('fits.gz').to_json(join=True) == {
            'id': 1,
            'name': 'fits.gz',
            'description': 'Gzip compressed FITS file.'
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading file_type from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['file_type']):
            assert FileType.from_id(i + 1).name == record['name']

    def test_id_missing(self) -> None:
        """Test exception on missing file_type `id`."""
        with pytest.raises(NotFound):
            FileType.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on file_type `id` already exists."""
        with pytest.raises(IntegrityError):
            FileType.add({'id': 1, 'name': 'jpeg',
                          'description': 'A bad format for scientific images.'})

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading file_type from `name`."""
        for record in testdata['file_type']:
            assert FileType.from_name(record['name']).name == record['name']

    def test_name_missing(self) -> None:
        """Test exception on missing file_type `name`."""
        with pytest.raises(NotFound):
            FileType.from_name('png')

    def test_name_already_exists(self) -> None:
        """Test exception on file_type `name` already exists."""
        with pytest.raises(IntegrityError):
            FileType.add({'name': 'fits.gz',
                          'description': 'Gzip compressed FITS file.'})


class TestFile:
    """Tests for `File` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create file instance and validate accessors."""
        for data in testdata['file']:
            file = File(**data)
            for key, value in data.items():
                assert getattr(file, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['file']:
            file = File.from_dict(data)
            assert data == file.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['file']:
            file = File.from_dict(data)
            assert tuple(data.values()) == file.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['file']:
            assert data == serializable(File(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert File.from_id(1).to_json(join=True) == {
            'id': 1,
            'observation_id': 19,
            'type_id': 1,
            'data': ['H4sICIVdxV8C/2xvY2FsXzMuZml0cwAAAAD//+zRMQrCMBjF8au8G2iLuDkoRghoKSRD1mhS6JBE',
                     'kjj09lbBLUEKHb/fAf48eILf+isDDiiQ2OAR/BCiS8gBFy4FUtbe6GhQdOKy56rc2+/mno5RTzA6',
                     'a+TpafFHd1RcoLKvnXv+5e42Igy/8uisT2Pwqd5ryr1mi8W+vXa9HlOSdefqH8t7nxghhBBCCFnN',
                     'GwAA///sxbEJAAAIAzCh///sILj1g2TJnNiuAwC8BQAA//8DABVnAU2AFgAA'],
            'type': FileType.from_id(1).to_json(join=True),
            'observation': Observation.from_id(19).to_json(join=True)
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading file from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['file']):
            assert File.from_id(i + 1).to_json(join=False) == {**record, 'id': i + 1}

    def test_id_missing(self) -> None:
        """Test exception on missing file `id`."""
        with pytest.raises(NotFound):
            File.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on file `id` already exists."""
        with pytest.raises(IntegrityError):
            File.add({'id': 1, 'observation_id': 1, 'type_id': 1, 'data': b'...'})

    def test_from_observation(self, testdata: TestData) -> None:
        """Test loading file from `observation_id`."""
        for i, record in enumerate(testdata['file']):
            assert File.from_observation(record['observation_id']).to_json(join=False) == {**record, 'id': i + 1}

    def test_observation_missing(self) -> None:
        """Test exception on missing file `observation_id`."""
        with pytest.raises(NotFound):
            File.from_observation(-1)

    def test_observation_already_exists(self) -> None:
        """Test exception on file `observation` already exists."""
        with pytest.raises(IntegrityError):
            File.add({'observation_id': File.from_id(1).observation_id, 'type_id': 1, 'data': b'...'})


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
            assert data == serializable(Forecast(**data).to_json(join=False))

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


class TestRecommendationGroup:
    """Tests for `RecommendationGroup` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create recommendation_group instance and validate accessors."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup(**data)
            for key, value in data.items():
                assert getattr(recommendation_group, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup.from_dict(data)
            assert data == recommendation_group.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['recommendation_group']:
            recommendation_group = RecommendationGroup.from_dict(data)
            assert tuple(data.values()) == recommendation_group.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['recommendation_group']:
            assert data == serializable(RecommendationGroup(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert RecommendationGroup.from_id(1).to_json(join=True) == {
            'id': 1,
            'created': '2020-10-24 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading recommendation_group from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['recommendation_group']):
            assert RecommendationGroup.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing recommendation_group `id`."""
        with pytest.raises(NotFound):
            RecommendationGroup.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on recommendation_group `id` already exists."""
        with pytest.raises(IntegrityError):
            RecommendationGroup.add({'id': 1})

    def test_new(self) -> None:
        """Test the creation of a new recommendation_group."""
        assert RecommendationGroup.count() == 3
        group = RecommendationGroup.new()
        assert RecommendationGroup.count() == 4
        RecommendationGroup.delete(group.id)
        assert RecommendationGroup.count() == 3

    def test_latest(self) -> None:
        """Test query for latest recommendation_group."""
        assert RecommendationGroup.latest().to_json(join=True) == {
            'id': 3,
            'created': '2020-10-26 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
        }

    def test_select_with_limit(self) -> None:
        """Test the selection of recommendation_group with a limit."""
        assert [group.to_json(join=True) for group in RecommendationGroup.select(limit=2)] == [
            {
                'id': 3,
                'created': '2020-10-26 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            },
            {
                'id': 2,
                'created': '2020-10-25 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            }
        ]

    def test_select_with_limit_and_offset(self) -> None:
        """Test the selection of recommendation_group with a limit and offset."""
        assert [group.to_json(join=True) for group in RecommendationGroup.select(limit=2, offset=1)] == [
            {
                'id': 2,
                'created': '2020-10-25 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            },
            {
                'id': 1,
                'created': '2020-10-24 20:01:00' + ('' if config.backend == 'sqlite' else '-04:00')
            }
        ]


class TestRecommendation:
    """Tests for `Recommendation` database model."""

    def test_init(self, testdata: TestData) -> None:
        """Create recommendation instance and validate accessors."""
        for data in testdata['recommendation']:
            recommendation = Recommendation(**data)
            for key, value in data.items():
                assert getattr(recommendation, key) == value

    def test_dict(self, testdata: TestData) -> None:
        """Test round-trip of dict translations."""
        for data in testdata['recommendation']:
            recommendation = Recommendation.from_dict(data)
            assert data == recommendation.to_dict()

    def test_tuple(self, testdata: TestData) -> None:
        """Test tuple-conversion."""
        for data in testdata['recommendation']:
            recommendation = Recommendation.from_dict(data)
            assert tuple(data.values()) == recommendation.to_tuple()

    def test_embedded_no_join(self, testdata: TestData) -> None:
        """Tests embedded method to check JSON-serialization."""
        for data in testdata['recommendation']:
            assert data == serializable(Recommendation(**data).to_json(join=False))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and full join."""
        assert Recommendation.from_id(1).to_json(join=True) == {
            'id': 1,
            'group_id': 1,
            'time': '2020-10-24 20:02:00' + ('' if config.backend == 'sqlite' else '-4:00'),
            'priority': 1,
            'object_id': 1,
            'facility_id': 1,
            'user_id': 2,
            'forecast_id': 1,
            'predicted_observation_id': 11,
            'observation_id': 19,
            'accepted': True,
            'rejected': False,
            'data': {},
            'group': RecommendationGroup.from_id(1).to_json(join=True),
            'user': User.from_id(2).to_json(join=True),
            'facility': Facility.from_id(1).to_json(join=True),
            'object': Object.from_id(1).to_json(join=True),
            'forecast': Forecast.from_id(1).to_json(join=True),
            'predicted': Observation.from_id(11).to_json(join=True),
            'observed': Observation.from_id(19).to_json(join=True),
            }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading recommendation from `id`."""
        # NOTE: `id` not set until after insert
        for i, record in enumerate(testdata['recommendation']):
            assert Recommendation.from_id(i + 1).id == i + 1

    def test_id_missing(self) -> None:
        """Test exception on missing recommendation `id`."""
        with pytest.raises(NotFound):
            Recommendation.from_id(-1)

    def test_id_already_exists(self) -> None:
        """Test exception on recommendation `id` already exists."""
        with pytest.raises(IntegrityError):
            Recommendation.add({'id': 1, 'group_id': 1, 'priority': 1, 'object_id': 1,
                                'facility_id': 1, 'user_id': 2})

    def test_for_user(self) -> None:
        """Test query for all recommendations for a given user."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 3

    def test_for_user_with_group_id(self) -> None:
        """Test query for all recommendations for a given user and group."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id, group_id=3)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 3

    def test_for_user_with_group_id_2(self) -> None:
        """Test query for all recommendations for a given user and group."""
        user_id = User.from_alias('tomb_raider').id
        results = Recommendation.for_user(user_id, group_id=2)
        assert len(results) == 4
        for record in results:
            assert record.user_id == user_id
            assert record.group_id == 2

    def test_next(self) -> None:
        """Test query for latest recommendation."""

        user_id = User.from_alias('tomb_raider').id
        response = Recommendation.next(user_id=user_id)
        assert len(response) == 0  # NOTE: all accepted already

        rec_id = Recommendation.for_user(user_id)[0].id
        Recommendation.update(rec_id, accepted=False)

        response = Recommendation.next(user_id=user_id)
        assert len(response) == 1

        Recommendation.update(rec_id, accepted=True)
        response = Recommendation.next(user_id=user_id)
        assert len(response) == 0


# TODO: TestModelType
# TODO: TestModel
