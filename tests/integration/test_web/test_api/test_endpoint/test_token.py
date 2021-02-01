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
from functools import cached_property

# internal libs
from refitt.web.request import format_request
from refitt.web.api.response import RESPONSE_MAP, PermissionDenied
from tests.integration.test_web.test_api import temp_secret, restore_session
from tests.integration.test_web.test_api.test_endpoint import LoginEndpoint, Endpoint

# external libs
import requests


TOKEN_PATTERN: re.Pattern = re.compile(r'^[a-zA-Z0-9_=-]+$')


class TestToken(LoginEndpoint):
    """Integration tests for /token endpoints."""

    route: str = '/token'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_get_token(self) -> None:
        client = self.get_client(self.user)
        with restore_session(client.id):
            with temp_secret(client.id) as secret:
                response = requests.get(format_request(self.route), auth=(client.key, secret.value))
                assert response.status_code == 200
                content = response.json()
                assert content['Status'] == 'Success'
                assert TOKEN_PATTERN.match(content['Response']['token'])


class TestTokenAdmin(Endpoint):
    """Integration tests for /token/<user_id> endpoints."""

    admin: str = 'superman'
    user: str = 'tomb_raider'

    @cached_property
    def route(self) -> str:
        user_id = self.get_client(self.user).user_id
        return f'/token/{user_id}'

    def test_get_token(self) -> None:
        admin = self.get_client(self.admin)
        client = self.get_client(self.user)
        with restore_session(client.id):
            status, payload = self.get(self.route, client_id=admin.id)
            assert status == 200
            assert payload['Status'] == 'Success'
            assert TOKEN_PATTERN.match(payload['Response']['token'])

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient'
            }
        )

