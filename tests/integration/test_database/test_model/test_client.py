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

"""Database client model integration tests."""


# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import Client, User, NotFound
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


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
            assert embedded_data == json_roundtrip(Client(**data).to_json(join=False))

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
        user = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                         'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4
        key, secret, client = Client.new(user.id)
        assert User.count() == 5 and Client.count() == 5
        Client.delete(client.id)
        assert User.count() == 5 and Client.count() == 4
        User.delete(user.id)
        assert User.count() == 4 and Client.count() == 4

    def test_delete_user_cascade(self) -> None:
        """Add a new user and client record and then remove them."""
        assert User.count() == 4 and Client.count() == 4
        user = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                         'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4
        Client.new(user.id)
        assert User.count() == 5 and Client.count() == 5
        User.delete(user.id)
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
