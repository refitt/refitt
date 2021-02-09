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

"""Integration tests for /info endpoints."""


# internal libs
from refitt.web.api.endpoint import INFO
from refitt.web.api.response import STATUS
from tests.integration.test_web.test_api.test_endpoint import Endpoint
from tests.integration.test_database.test_model import json_roundtrip


class TestInfoFull(Endpoint):
    """Test /info endpoints."""

    route: str = '/info'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_get(self) -> None:
        status, payload = self.get(self.route, client_id=1)
        assert status == STATUS['OK']
        assert payload == {'Status': 'Success', 'Response': json_roundtrip(INFO)}


class TestInfoPartial(Endpoint):
    """Test /info/<resource> endpoints."""

    admin: str = 'superman'
    user: str = 'tomb_raider'
    resource: str = 'client'

    @property
    def route(self) -> str:
        return f'/info/{self.resource}'

    def test_get(self) -> None:
        for resource, info in INFO.items():
            self.resource = resource
            status, payload = self.get(self.route, client_id=1)
            assert status == STATUS['OK']
            assert payload == {'Status': 'Success', 'Response': json_roundtrip(info)}
