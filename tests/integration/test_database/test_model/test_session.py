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

"""Database session model integration tests."""


# standard libs
from datetime import datetime

# external libs
import pytest
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.database import config
from refitt.database.model import Session, Client, NotFound, User
from refitt.web.token import JWT
from tests.integration.test_database.test_model.conftest import TestData
from tests.integration.test_database.test_model import json_roundtrip


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
            assert embedded_data == json_roundtrip(Session(**data).to_json(join=False))

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
            assert Session.from_id(id).client.user.alias == testdata['user'][id - 1]['alias']

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
        user = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                         'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4 and Session.count() == 4
        key, secret, client = Client.new(user.id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        Session.new(user.id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 5
        Session.delete(Session.from_client(client.id).id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        User.delete(user.id)  # NOTE: deletes client
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4

    def test_delete_client_cascade(self) -> None:
        """Add a new user, client, and session. Remove user to clear client and session."""
        assert User.count() == 4 and Client.count() == 4 and Session.count() == 4
        user = User.add({'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                         'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        assert User.count() == 5 and Client.count() == 4 and Session.count() == 4
        Client.new(user.id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 4
        Session.new(user.id)
        assert User.count() == 5 and Client.count() == 5 and Session.count() == 5
        User.delete(user.id)
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
