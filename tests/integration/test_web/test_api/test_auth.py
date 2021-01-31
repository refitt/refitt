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

"""Integration tests for API authentication."""

# standard libs
from contextlib import contextmanager

# internal libs
from refitt.web import request
from refitt.web.token import Secret, Token, TokenInvalid, TokenNotFound, TokenExpired
from refitt.web.api.auth import AuthenticationNotFound, AuthenticationInvalid, PermissionDenied
from refitt.web.api.response import RESPONSE_MAP
from refitt.database.model import User, Client, Session
from tests.integration.test_web.test_api import temp_secret

# external libs
import requests as _requests


@contextmanager
def temp_revoke_access(client_id: int) -> None:
    """Temporarily revoke access (i.e., client.valid = false)."""
    previous = Client.from_id(client_id).valid
    try:
        Client.update(client_id, valid=False)
        yield
    finally:
        Client.update(client_id, valid=previous)


@contextmanager
def temp_expired_token(client_id: int) -> str:
    """Temporarily yield a token that is expired. Fix in database after."""
    client = Client.from_id(client_id)
    session = Session.from_client(client_id)
    old_token = session.token
    try:
        # set token to have expired yesterday
        yield Session.new(client.user_id, -86400).encrypt()
    finally:
        Session.update(session.id, token=old_token)


class TestRequestAuth:
    """Integration tests for API authentication."""

    def test_auth_not_found(self) -> None:
        url = request.format_request('/token')
        response = _requests.get(url)
        assert response.status_code == RESPONSE_MAP[AuthenticationNotFound]
        assert response.json() == {'Status': 'Error',
                                   'Message': 'Missing key:secret in header'}

    def test_key_invalid(self) -> None:
        url = request.format_request('/token')
        response = _requests.get(url, auth=('my-key', 'my-secret'))
        assert response.status_code == RESPONSE_MAP[AuthenticationInvalid]
        assert response.json() == {'Status': 'Error',
                                   'Message': 'Client key invalid'}

    def test_secret_not_real(self) -> None:
        url = request.format_request('/token')
        user = User.from_alias('tomb_raider')
        client = Client.from_user(user.id)
        response = _requests.get(url, auth=(client.key, 'my-secret'))
        assert response.status_code == RESPONSE_MAP[AuthenticationInvalid]
        assert response.json() == {'Status': 'Error',
                                   'Message': 'Client secret invalid'}

    def test_secret_invalid(self) -> None:
        url = request.format_request('/token')
        user = User.from_alias('tomb_raider')
        client = Client.from_user(user.id)
        response = _requests.get(url, auth=(client.key, Secret.generate().value))
        assert response.status_code == RESPONSE_MAP[AuthenticationInvalid]
        assert response.json() == {'Status': 'Error',
                                   'Message': 'Client secret invalid'}

    def test_access_revoked(self) -> None:
        url = request.format_request('/token')
        user = User.from_alias('tomb_raider')
        client = Client.from_user(user.id)
        with temp_secret(client.id) as secret:
            with temp_revoke_access(client.id):
                response = _requests.get(url, auth=(client.key, secret.value))
                assert response.status_code == RESPONSE_MAP[PermissionDenied]
                assert response.json() == {'Status': 'Error',
                                           'Message': 'Access has been revoked'}

    def test_token_missing(self) -> None:
        url = request.format_request('/info')
        response = _requests.get(url)
        assert response.status_code == RESPONSE_MAP[TokenNotFound]
        assert response.json() == {'Status': 'Error',
                                   'Message': 'Expected "Authorization: Bearer <token>" in header'}

    # dummy token for tests
    BAD_TOKEN: Token = Token('bad-token')

    def test_token_invalid(self) -> None:
        try:
            with request.use_token('bad-token'):
                request.get('/info')
        except request.APIError as error:
            status, message = error.args
            assert status == RESPONSE_MAP[TokenInvalid]
            assert message == f'Token invalid: \'bad...ken\''
        else:
            raise AssertionError('Expected invalid token')

    def test_token_expired(self) -> None:
        user = User.from_alias('tomb_raider')
        client = Client.from_user(user.id)
        with temp_expired_token(client.id) as token:
            with request.use_token(token):
                try:
                    request.get('/info')
                except request.APIError as error:
                    status, message = error.args
                    assert status == RESPONSE_MAP[TokenExpired]
                    assert message == f'Token expired'
                else:
                    raise AssertionError('Expected expired token')
