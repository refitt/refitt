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

"""Integration tests for /source endpoints."""


# internal libs
from refitt.database.model import Source, SourceType
from refitt.web.api.response import STATUS, RESPONSE_MAP, NotFound, PermissionDenied, ParameterInvalid
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestGetSource(Endpoint):
    """Tests for GET /source/<id> endpoint."""

    route: str = '/source/2'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('delta_one_bourne_12in')
        assert self.get(f'/source/{source.id}', client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Source is not public',
            }
        )

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('tomb_raider_croft_4m')
        assert self.get(f'/source/{source.id}', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source': source.to_json(join=False)},
            }
        )

    def test_get_with_join(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('tomb_raider_croft_4m')
        assert self.get(f'/source/{source.id}', client_id=client.id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source': source.to_json(join=True)},
            }
        )

    def test_source_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/source/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No source with id=0',
            }
        )


class TestGetSourceType(Endpoint):
    """Tests for GET /source/type/<id> endpoint."""

    route: str = '/source/type/2'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        source_type = SourceType.from_id(2)
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source_type': source_type.to_json(join=False)},
            }
        )

    def test_source_type_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/source/type/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No source_type with id=0',
            }
        )


class TestGetSourceSourceType(Endpoint):
    """Tests for GET /source/<id>/type endpoint."""

    route: str = '/source/5/type'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_source_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/source/0/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No source with id=0',
            }
        )

    def test_get(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('tomb_raider_croft_4m')
        assert self.get(f'/source/{source.id}/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source_type': source.type.to_json(join=False)},
            }
        )


class TestGetSourceUser(Endpoint):
    """Tests for GET /source/<id>/user endpoint."""

    route: str = '/source/5/user'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_source_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/source/0/user', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No source with id=0',
            }
        )

    def test_get(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('tomb_raider_croft_4m')
        assert self.get(f'/source/{source.id}/user', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'user': source.user.to_json(join=False)},
            }
        )


class TestGetSourceFacility(Endpoint):
    """Tests for GET /source/<id>/facility endpoint."""

    route: str = '/source/5/facility'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_source_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/source/0/facility', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No source with id=0',
            }
        )

    def test_get(self) -> None:
        client = self.get_client(self.user)
        source = Source.from_name('tomb_raider_croft_4m')
        assert self.get(f'/source/{source.id}/facility', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'facility': source.facility.to_json(join=False)},
            }
        )
