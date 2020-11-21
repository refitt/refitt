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

# internal libs
from refitt.database.model import User, Facility, FacilityMap, Client, Session
from refitt.web.token import JWT


# test data fixture return type
Record = Dict[str, Any]
Records = List[Record]
TestData = Dict[str, Records]


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
            assert data == json.loads(json.dumps(User(**data).embedded()))

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading user profile from `id`."""
        # NOTE: `id` not set until after insert
        for i, user in enumerate(testdata['user']):
            assert User.from_id(i + 1).alias == user['alias']

    def test_from_email(self, testdata: TestData) -> None:
        """Test loading user profile from `email`."""
        for user in testdata['user']:
            assert User.from_email(user['email']).email == user['email']

    def test_from_alias(self, testdata: TestData) -> None:
        """Test loading user profile from `alias`."""
        for user in testdata['user']:
            assert User.from_alias(user['alias']).alias == user['alias']

    def test_add_remove(self) -> None:
        """Add a new user record and then remove it."""
        assert User.count() == 3
        User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                  'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 4
        assert User.from_alias('007').last_name == 'Bond'
        User.delete(User.from_alias('007').id)
        assert User.count() == 3

    def test_update_email(self) -> None:
        """Update email address of user profile."""
        old_email, new_email = 'bourne@cia.gov', 'jason.bourne@cia.gov'
        assert User.from_id(1).email == old_email
        User.update(1, email=new_email)
        assert User.from_id(1).email == User.from_email(new_email).email
        User.update(1, email=old_email)
        assert User.from_id(1).email == User.from_email(old_email).email

    def test_update_data(self) -> None:
        """Update custom data of user profile."""
        old_data = {'user_type': 'amateur'}
        new_data = {'user_type': 'amateur', 'special_field': 42}
        assert User.from_alias('tomb_raider').data == old_data
        User.update(2, special_field=42)
        assert User.from_alias('tomb_raider').data == new_data
        User.update(2, data=old_data)
        assert User.from_alias('tomb_raider').data == old_data

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
        """Create a new user, with facility, then remove."""
        assert User.count() == 3 and Facility.count() == 4 and FacilityMap.count() == 4
        User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                  'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        user = User.from_alias('007')
        Facility.add({'name': 'Bond_4m', 'latitude': -25.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})
        facility = Facility.from_name('Bond_4m')
        user.add_facility(facility.id)
        assert user.facilities()[0].to_dict() == facility.to_dict()
        assert User.count() == 4 and Facility.count() == 5 and FacilityMap.count() == 5
        User.delete(user.id)
        assert User.count() == 3 and Facility.count() == 5 and FacilityMap.count() == 4
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
            assert data == json.loads(json.dumps(Facility(**data).embedded()))

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading facility profile from `id`."""
        # NOTE: `id` not set until after insert
        for i, facility in enumerate(testdata['facility']):
            assert Facility.from_id(i + 1).name == facility['name']

    def test_from_name(self, testdata: TestData) -> None:
        """Test loading facility profile from `name`."""
        for facility in testdata['facility']:
            assert Facility.from_name(facility['name']).name == facility['name']

    def test_delete(self) -> None:
        """Add a new facility record and then delete it."""
        assert Facility.count() == 4
        Facility.add({'name': 'Croft_10m', 'latitude': -25.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 20.5})
        assert Facility.count() == 5
        assert Facility.from_name('Croft_10m').limiting_magnitude == 20.5
        Facility.delete(Facility.from_name('Croft_10m').id)
        assert Facility.count() == 4

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

    def test_delete_facility_map_cascade(self) -> None:
        """Create a new facility, associate it with a user, then remove."""
        assert User.count() == 3 and Facility.count() == 4 and FacilityMap.count() == 4
        Facility.add({'name': 'Bourne_4m', 'latitude': -25.5, 'longitude': -69.25, 'elevation': 5050,
                      'limiting_magnitude': 17.5, 'data': {'telescope_design': 'reflector'}})
        facility = Facility.from_name('Bourne_4m')
        user = User.from_alias('delta_one')
        user.add_facility(facility.id)
        assert User.count() == 3 and Facility.count() == 5 and FacilityMap.count() == 5
        Facility.delete(facility.id)
        assert User.count() == 3 and Facility.count() == 4 and FacilityMap.count() == 4


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
            assert data == json.loads(json.dumps(Client(**data).embedded(join=False)))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Client.from_id(1).embedded() == {
            "id": 1,
            "user_id": 1,
            "level": 5,
            "key": "78h6IuhW30Re7I-C",
            "secret": "7ccb08b171f4a28e6b5f2af5597153873d7cd90a972f2bee7b8ac82c43e0e4e9",
            "valid": True,
            "created": "2020-10-23 17:45:01-04:00",
            "user": {
                "id": 1,
                "first_name": "Jason",
                "last_name": "Bourne",
                "email": "bourne@cia.gov",
                "alias": "delta_one",
                "data": {
                    "user_type": "amateur"
                }
            }
        }

    def test_from_id(self, testdata: TestData) -> None:
        """Test loading client from `id`."""
        # NOTE: `id` not set until after insert
        for i, client in enumerate(testdata['client']):
            assert Client.from_id(i + 1).user.alias == testdata['user'][i]['alias']

    def test_from_user(self) -> None:
        """Test loading client from `user`."""
        for id in range(1, 4):
            assert id == Client.from_user(id).user_id == User.from_id(id).id

    def test_relationship_user(self) -> None:
        """Test user foreign key relationship."""
        for id in range(1, 4):
            assert id == Client.from_user(id).user.id == User.from_id(id).id

    def test_delete(self) -> None:
        """Add a new user and client. Remove the client directly."""
        assert User.count() == 3 and Client.count() == 3
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 4 and Client.count() == 3
        key, secret, client = Client.new(user_id)
        assert User.count() == 4 and Client.count() == 4
        Client.delete(client.id)
        assert User.count() == 4 and Client.count() == 3
        User.delete(user_id)
        assert User.count() == 3 and Client.count() == 3

    def test_delete_user_cascade(self) -> None:
        """Add a new user and client record and then remove them."""
        assert User.count() == 3 and Client.count() == 3
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 4 and Client.count() == 3
        Client.new(user_id)
        assert User.count() == 4 and Client.count() == 4
        User.delete(user_id)
        assert User.count() == 3 and Client.count() == 3

    def test_new_secret(self) -> None:
        """Generate a new client secret and then manually reset it back."""
        old_hash = Client.from_id(1).secret
        new_hash = Client.new_secret(1).hashed().value
        assert new_hash != old_hash
        Client.update(1, secret=old_hash)
        assert Client.from_id(1).secret == old_hash

    def test_new_key_and_secret(self) -> None:
        """Generate a new client key and secret and then manually reset them."""
        data = Client.from_id(1).to_dict()
        old_key, old_secret_hash = data['key'], data['secret']
        key, secret = Client.new_key(1)
        assert key.value != old_key and secret.hashed().value != old_secret_hash
        Client.update(1, key=old_key, secret=old_secret_hash)
        client = Client.from_id(1)
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
            assert data == json.loads(json.dumps(Session(**data).embedded(join=False)))

    def test_embedded(self) -> None:
        """Test embedded method to check JSON-serialization and auto-join."""
        assert Session.from_id(1).embedded() == {
            'id': 1,
            'client_id': 1,
            'expires': '2020-10-23 18:00:01-04:00',
            'token': 'c44d20d18e734aea40b30682a57162b53c18f676c1b752696dad5dc6586187fe',
            'created': '2020-10-23 17:45:01-04:00',
            'client': {'id': 1,
                       'user_id': 1,
                       'level': 5,
                       'key': '78h6IuhW30Re7I-C',
                       'secret': '7ccb08b171f4a28e6b5f2af5597153873d7cd90a972f2bee7b8ac82c43e0e4e9',
                       'valid': True,
                       'created': '2020-10-23 17:45:01-04:00',
                       'user': {'id': 1,
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

    def test_from_client(self) -> None:
        """Test loading session from `client`."""
        for id in range(1, 4):
            assert id == Session.from_client(id).client_id == Client.from_id(id).id

    def test_relationship_client(self) -> None:
        """Test client foreign key relationship."""
        for id in range(1, 4):
            assert id == Session.from_client(id).client.id == Client.from_id(id).id

    def test_delete(self) -> None:
        """Add a new session and remove it directly."""
        assert User.count() == 3 and Client.count() == 3 and Session.count() == 3
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 4 and Client.count() == 3 and Session.count() == 3
        key, secret, client = Client.new(user_id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 3
        Session.new(user_id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4
        Session.delete(Session.from_client(client.id).id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 3
        User.delete(user_id)  # NOTE: deletes client
        assert User.count() == 3 and Client.count() == 3 and Session.count() == 3

    def test_delete_client_cascade(self) -> None:
        """Add a new user, client, and session. Remove user to clear client and session."""
        assert User.count() == 3 and Client.count() == 3 and Session.count() == 3
        user_id = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 4 and Client.count() == 3 and Session.count() == 3
        Client.new(user_id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 3
        Session.new(user_id)
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4
        User.delete(user_id)
        assert User.count() == 3 and Client.count() == 3 and Session.count() == 3

    def test_new_token(self) -> None:
        """Generate a new client secret and then manually reset it back."""
        session = Session.from_client(1)
        before = session.created
        assert datetime.now().astimezone() > before
        old_hash = session.token
        expired = session.expires
        jwt = Session.new(1)
        assert isinstance(jwt, JWT)
        assert jwt.exp > datetime.now()
        new_session = Session.from_client(1)
        assert new_session.created > before
        assert new_session.token != old_hash and len(new_session.token) == len(old_hash)
        Session.update(1, token=old_hash, created=before, expires=expired)  # NOTE: hard reset
        new_session = Session.from_client(1)
        assert new_session.created == before
        assert new_session.token == old_hash
        assert new_session.expires == expired
