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

"""Integration tests for /user endpoints."""


# external libs
import pytest

# internal libs
from refitt.database.model import Facility
from refitt.web.api.response import (STATUS, RESPONSE_MAP, NotFound, ConstraintViolation, PermissionDenied,
                                     PayloadNotFound, PayloadMalformed, PayloadInvalid, ParameterInvalid)
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestAddFacility(Endpoint):
    """Tests for POST /facility endpoint."""

    route: str = '/facility'
    method: str = 'post'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: only needed for permission denied check

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.post(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_payload_missing(self) -> None:
        client = self.get_client(self.admin)
        assert self.post(self.route, client_id=client.id) == (
            RESPONSE_MAP[PayloadNotFound], {
                'Status': 'Error',
                'Message': 'Missing data in request',
            }
        )

    def test_payload_malformed(self) -> None:
        client = self.get_client(self.admin)
        assert self.post(self.route, client_id=client.id, data=b'abc...') == (
            RESPONSE_MAP[PayloadMalformed], {
                'Status': 'Error',
                'Message': 'Invalid JSON data',
            }
        )

    def test_payload_invalid(self) -> None:
        client = self.get_client(self.admin)
        assert self.post(self.route, client_id=client.id, json={'foo': 42}) == (
            RESPONSE_MAP[PayloadInvalid], {
                'Status': 'Error',
                'Message': 'Payload content invalid: (\'foo\' is an invalid keyword argument for Facility)',
            }
        )

    def test_new(self) -> None:
        admin = self.get_client(self.admin)
        with pytest.raises(Facility.NotFound):
            Facility.from_name('Croft_10m')
        data = {'name': 'Croft_10m', 'latitude': -24.5, 'longitude': -69.25,
                'elevation': 5050, 'limiting_magnitude': 20.5}
        status, payload = self.post(self.route, client_id=admin.id, json=data)
        facility_id = payload['Response']['facility']['id']
        assert status == STATUS['OK']
        assert payload == {
            'Status': 'Success',
            'Response': {'facility': {'id': int(facility_id)}}
        }
        Facility.delete(facility_id)
        with pytest.raises(Facility.NotFound):
            Facility.from_name('Croft_10m')

    def test_update(self) -> None:
        admin = self.get_client(self.admin)
        data = Facility.from_name('Croft_4m').to_dict()
        status, payload = self.post(self.route, client_id=admin.id, json={
            'id': data['id'], 'limiting_magnitude': 17.9, })
        assert status == STATUS['OK']
        assert payload == {'Status': 'Success',
                           'Response': {'facility': {'id': data['id']}}}
        assert Facility.from_name('Croft_4m').to_dict() == {**data, 'limiting_magnitude': 17.9}
        Facility.update(data['id'], limiting_magnitude=17.5)
        assert Facility.from_name('Croft_4m').to_dict() == data

    def test_facility_name_already_exists(self) -> None:
        admin = self.get_client(self.admin)
        data = {'name': 'Croft_4m', 'latitude': -24.5, 'longitude': -69.25,
                'elevation': 5050, 'limiting_magnitude': 20.5}
        status, payload = self.post(self.route, client_id=admin.id, json=data)
        assert status == RESPONSE_MAP[ConstraintViolation]
        assert payload['Status'] == 'Error'
        assert 'facility' in payload['Message'] and 'name' in payload['Message']
        # NOTE: exact message depends on backend database error message formatting

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        data = {'name': 'Croft_4m', 'latitude': -24.5, 'longitude': -69.25,
                'elevation': 5050, 'limiting_magnitude': 20.5}
        assert self.post(self.route, client_id=admin.id, json=data, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )


class TestGetFacility(Endpoint):
    """Tests for GET /facility/<id> endpoint."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_get(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {
                    'facility': {
                        'id': 3,
                        'name': 'Croft_4m',
                        'latitude': -24.5,
                        'longitude': -69.25,
                        'elevation': 5050.0,
                        'limiting_magnitude': 17.5,
                        'data': {'telescope_design': 'reflector'}
                    }
                }
            }
        )

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/facility/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
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


class TestAlterFacility(Endpoint):
    """Tests for PUT /facility/<id>?... endpoint."""

    method: str = 'put'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_alter_limiting_magnitude(self) -> None:
        data = Facility.from_name('Croft_4m').to_dict()
        admin = self.get_client(self.admin)
        assert self.put(self.route, client_id=admin.id, limiting_magnitude=17.9) == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'facility': {**data, 'limiting_magnitude': 17.9}}})
        assert self.put(self.route, client_id=admin.id, limiting_magnitude=17.5) == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'facility': data}})

    def test_alter_telescope_type(self) -> None:
        data = Facility.from_name('Croft_4m').to_dict()
        admin = self.get_client(self.admin)
        assert self.put(self.route, client_id=admin.id, telescope_design='awesome') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'facility': {**data, 'data': {**data['data'], 'telescope_design': 'awesome'}}}})
        assert self.put(self.route, client_id=admin.id, telescope_design='reflector') == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'facility': data}})

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/facility/0', client_id=admin.id, limiting_magnitude=100) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )


class TestDeleteFacility(Endpoint):
    """Tests for DELETE /facility endpoint."""

    route: str = '/facility/0'  # NOTE: facility_id not important because Endpoint tests don't get to it
    method: str = 'delete'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    def test_permission_denied(self) -> None:
        # NOTE: the actual id doesn't matter because permission denied
        client = self.get_client(self.user)
        assert self.delete(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_delete(self) -> None:
        client = self.get_client(self.admin)
        with pytest.raises(Facility.NotFound):
            Facility.from_name('Croft_10m')
        data = {'name': 'Croft_10m', 'latitude': -24.5, 'longitude': -69.25,
                'elevation': 5050, 'limiting_magnitude': 20.5}
        status, payload = self.post('/facility', client_id=client.id, json=data)
        facility_id = payload['Response']['facility']['id']
        assert status == STATUS['OK']
        assert payload == {
            'Status': 'Success',
            'Response': {'facility': {'id': int(facility_id)}}
        }
        status, payload = self.delete(f'/facility/{facility_id}', client_id=client.id)
        assert status == STATUS['OK']
        assert payload == {'Status': 'Success', 'Response': {'facility': {'id': facility_id}}}
        with pytest.raises(Facility.NotFound):
            Facility.from_name('Croft_10m')

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/facility/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/facility/0', client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )


class TestGetAllFacilityUser(Endpoint):
    """Tests for GET /facility/<id>/user endpoints."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}/user'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/facility/0/user', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )

    def test_get_all(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id) == (
            STATUS['OK'],  {
                'Status': 'Success',
                'Response': {
                    'user': [
                        {
                            'id': 3,
                            'first_name': 'Lara',
                            'last_name': 'Croft',
                            'email': 'lara@croft.net',
                            'alias': 'tomb_raider',
                            'data': {'user_type': 'amateur'},
                        }
                    ]
                }
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


class TestGetOneFacilityUser(Endpoint):
    """Tests for GET /facility/<id>/user/<id> endpoints."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}/user/3'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_get_one(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {
                    'user': {
                            'id': 3,
                            'first_name': 'Lara',
                            'last_name': 'Croft',
                            'email': 'lara@croft.net',
                            'alias': 'tomb_raider',
                            'data': {'user_type': 'amateur'},
                        }
                }
            }
        )

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/facility/0/user/3', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/facility/3/user/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'User (0) not associated with facility (3)',
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


class TestAddFacilityUser(Endpoint):
    """Tests for PUT /facility/<id>/user/<id> endpoints."""

    method: str = 'put'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}/user/2'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.put(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_put(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'User (2) not associated with facility (3)', })
        assert self.put(self.route, client_id=admin.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {}, })
        assert self.delete(self.route, client_id=admin.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {}, })
        assert self.get(self.route, client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'User (2) not associated with facility (3)', })

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/facility/0/user/2', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/facility/3/user/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )


class TestRemoveFacilityUser(Endpoint):
    """Tests for PUT /facility/<id>/user/<id> endpoints."""

    method: str = 'delete'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        facility_id = Facility.from_name('Croft_4m').id
        return f'/facility/{facility_id}/user/4'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.put(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    # NOTE: See TestAddFacilityUser.test_put for successful delete

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/facility/0/user/2', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
            }
        )

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/facility/3/user/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete(self.route, client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )
