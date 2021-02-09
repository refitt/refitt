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

"""Integration tests for /client endpoints."""


# standard libs
import re
from abc import ABC
from functools import cached_property

# internal libs
from refitt.web.api.response import STATUS, RESPONSE_MAP, PermissionDenied, RecordNotFound
from tests.integration.test_web.test_api.test_endpoint import Endpoint
from tests.integration.test_web.test_api import restore_client


KEY_PATTERN: re.Pattern = re.compile(r'^[a-zA-Z0-9_=-]{16}$')
SECRET_PATTERN: re.Pattern = re.compile(r'^[a-zA-Z0-9_=-]{64}$')


class ClientEndpoint(Endpoint, ABC):
    """Common tests to /client/... endpoints."""

    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_get(self) -> None:
        with restore_client(self.get_client(self.user).id):
            status, payload = self.get(self.route, client_id=self.get_client(self.admin).id)
            assert status == STATUS['OK']
            assert list(payload.keys()) == ['Status', 'Response']
            assert list(payload['Response'].keys()) == ['client']
            assert list(payload['Response']['client'].keys()) == ['key', 'secret']
            assert payload['Status'] == 'Success'
            assert KEY_PATTERN.match(payload['Response']['client']['key'])
            assert SECRET_PATTERN.match(payload['Response']['client']['secret'])


class TestClient(ClientEndpoint):
    """Integration tests for /client/<user_id> endpoints."""

    @cached_property
    def route(self) -> str:
        user_id = self.get_client(self.user).user_id
        return f'/client/{user_id}'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient'
            }
        )

    def test_user_not_found(self):
        assert self.get('/client/10', client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[RecordNotFound], {
                'Status': 'Error',
                'Message': 'No user with id=10'
            }
        )


class TestClientSecret(ClientEndpoint):
    """Integration tests for /client/secret/<user_id> endpoints."""

    @cached_property
    def route(self) -> str:
        user_id = self.get_client(self.user).user_id
        return f'/client/secret/{user_id}'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient'
            }
        )

    def test_user_not_found(self):
        assert self.get('/client/secret/10', client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[RecordNotFound], {
                'Status': 'Error',
                'Message': 'No user with id=10'
            }
        )


