# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for /epoch endpoints."""


# internal libs
from refitt.database.model import Epoch
from refitt.web.api.response import (STATUS, RESPONSE_MAP, NotFound, ParameterInvalid, ParameterNotFound,
                                     PayloadTooLarge)
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestGetEpochMany(Endpoint):
    """Tests for GET /epoch endpoint."""

    route: str = '/epoch'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=1, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_limit_missing(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Missing expected parameter: limit'
            }
        )

    def test_limit_too_large(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=1000) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': 'Must provide \'limit\' less than 100'
            }
        )

    def test_limit_not_integer(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit='abc') == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Expected integer for parameter: limit'
            }
        )

    def test_offset_not_integer(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=4, offset='abc') == (
            RESPONSE_MAP[ParameterNotFound], {
                'Status': 'Error',
                'Message': 'Expected integer for parameter: offset'
            }
        )

    def test_get_all(self) -> None:
        data = [group.to_json() for group in Epoch.select(20)]
        assert len(data) == 4
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=20) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'epoch': data},
            }
        )

    def test_get_with_limit(self) -> None:
        data = [group.to_json() for group in Epoch.select(20)]
        assert len(data) == 4
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'epoch': data[:2]},
            }
        )

    def test_get_with_offset_1(self) -> None:
        data = [group.to_json() for group in Epoch.select(20)]
        assert len(data) == 4
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2, offset=1) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'epoch': data[1:3]},
            }
        )

    def test_get_with_offset_2(self) -> None:
        data = [group.to_json() for group in Epoch.select(20)]
        assert len(data) == 4
        assert self.get(self.route, client_id=self.get_client(self.user).id, limit=2, offset=2) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'epoch': data[2:]},
            }
        )


class TestGetEpoch(Endpoint):
    """Tests for GET /epoch/<id> endpoint."""

    route: str = '/epoch/1'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_invalid_parameter(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )

    def test_not_found(self) -> None:
        assert self.get('/epoch/0', client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No epoch with id=0'
            }
        )

    def test_get(self) -> None:
        data = Epoch.from_id(1).to_json()
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'epoch': data},
            }
        )
