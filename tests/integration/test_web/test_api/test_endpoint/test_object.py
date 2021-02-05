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

"""Integration tests for /object endpoints."""


# internal libs
from refitt.database.model import Object, ObjectType
from refitt.web.api.response import STATUS, RESPONSE_MAP, NotFound, ParameterInvalid
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestGetObject(Endpoint):
    """Tests for GET /object/<id> endpoint."""

    route: str = '/object/1'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

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
        object = Object.from_id(1)
        assert self.get(f'/object/{object.id}', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object': object.to_json(join=False)},
            }
        )

    def test_get_by_id_with_join(self) -> None:
        client = self.get_client(self.user)
        object = Object.from_id(1)
        assert self.get(f'/object/{object.id}', client_id=client.id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object': object.to_json(join=True)},
            }
        )

    def test_object_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/object/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No object with id=0',
            }
        )


class TestGetObjectType(Endpoint):
    """Tests for GET /object/type/<id> endpoint."""

    route: str = '/object/type/2'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

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
        object_type = ObjectType.from_id(2)
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object_type': object_type.to_json(join=False)},
            }
        )

    def test_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/object/type/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No object_type with id=0',
            }
        )


class TestGetObjectObjectType(Endpoint):
    """Tests for GET /object/<id>/type endpoint."""

    route: str = '/object/2/type'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_object_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/object/0/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No object with id=0',
            }
        )

    def test_get(self) -> None:
        client = self.get_client(self.user)
        object = Object.from_id(2)
        assert self.get(f'/object/{object.id}/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object_type': object.type.to_json(join=False)},
            }
        )
