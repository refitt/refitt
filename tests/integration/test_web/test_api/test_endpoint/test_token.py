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

"""Integration tests for /token endpoints."""


# standard libs
import re
from contextlib import contextmanager

# internal libs
from refitt.web import request
from refitt.web.token import JWT
from refitt.web.api.response import RESPONSE_MAP, PermissionDenied
from refitt.database.model import Client, Session, User
from tests.integration.test_web.test_api import temp_secret

# external libs
import requests


@contextmanager
def restore_session(client_id: int) -> None:
    """Force restore token for session for given client."""
    client = Client.from_id(client_id)
    session = Session.from_client(client.id)
    try:
        yield
    finally:
        Session.update(session.id, token=session.token,
                       expires=session.expires, created=session.created)


TOKEN_PATTERN: re.Pattern = re.compile(r'[a-zA-Z0-9_=]+')


class TestTokenEndpoint:
    """Integration tests for /token endpoints."""

    def test_get_token(self) -> None:
        user = User.from_alias('tomb_raider')
        client = Client.from_user(user.id)
        with temp_secret(client.id) as secret:
            with restore_session(client.id):
                url = request.format_request('/token')
                response = requests.get(url, auth=(client.key, secret.value))
                assert response.status_code == 200
                content = response.json()
                assert content['Status'] == 'Success'
                assert TOKEN_PATTERN.match(content['Response']['token'])

    def test_get_token_by_admin(self) -> None:
        admin = Client.from_user(User.from_alias('superman').id)
        token = JWT(sub=admin.id, exp=None).encrypt()
        client = Client.from_user(User.from_alias('tomb_raider').id)
        with restore_session(client.id):
            url = request.format_request(f'/token/{client.user_id}')
            response = requests.get(url, headers={'Authorization': f'Bearer {token}'})
            assert response.status_code == 200
            content = response.json()
            assert content['Status'] == 'Success'
            assert TOKEN_PATTERN.match(content['Response']['token'])

    def test_get_token_by_admin_permission_denied(self) -> None:
        client = Client.from_user(User.from_alias('tomb_raider').id)
        token = JWT(sub=client.id, exp=None).encrypt()
        url = request.format_request(f'/token/{client.user_id}')
        response = requests.get(url, headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == RESPONSE_MAP[PermissionDenied]
        content = response.json()
        assert content['Status'] == 'Error'
        assert content['Message'] == 'Authorization level insufficient'

