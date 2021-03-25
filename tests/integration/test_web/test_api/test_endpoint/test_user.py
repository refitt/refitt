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
from refitt.database.model import User
from refitt.web.api.response import (STATUS, RESPONSE_MAP, NotFound, ConstraintViolation, PermissionDenied,
                                     PayloadNotFound, PayloadMalformed, PayloadInvalid, ParameterInvalid)
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestAddUser(Endpoint):
    """Tests for POST /user endpoint."""

    route: str = '/user'
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
                'Message': 'Payload content invalid: (\'foo\' is an invalid keyword argument for User)',
            }
        )

    def test_new(self) -> None:
        admin = self.get_client(self.admin)
        with pytest.raises(User.NotFound):
            User.from_alias('007')
        status, payload = self.post(self.route, client_id=admin.id, json={
            'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        user_id = payload['Response']['user']['id']
        assert status == STATUS['OK']
        assert payload == {
            'Status': 'Success',
            'Response': {'user': {'id': int(user_id)}}
        }
        User.delete(user_id)
        with pytest.raises(User.NotFound):
            User.from_alias('007')

    def test_update(self) -> None:
        admin = self.get_client(self.admin)
        data = User.from_alias(self.user).to_dict()
        status, payload = self.post(self.route, client_id=admin.id, json={
            'id': data['id'], 'email': 'lara@croft.com', })
        assert status == STATUS['OK']
        assert payload == {'Status': 'Success',
                           'Response': {'user': {'id': data['id']}}}
        User.update(data['id'], email=data['email'])
        assert data == User.from_alias(self.user).to_dict()

    def test_user_alias_already_exists(self) -> None:
        admin = self.get_client(self.admin)
        data = {'first_name': 'Lucy', 'last_name': 'Croft', 'email': 'lucy@croft.net', 'alias': 'tomb_raider'}
        status, payload = self.post(self.route, client_id=admin.id, json=data)
        assert status == RESPONSE_MAP[ConstraintViolation]
        assert payload['Status'] == 'Error'
        assert 'user' in payload['Message'] and 'alias' in payload['Message']
        # NOTE: exact message depends on backend database error message formatting

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        data = {'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
                'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}}
        assert self.post(self.route, client_id=admin.id, json=data, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )


class TestGetUser(Endpoint):
    """Tests for GET /user/<id> endpoint."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}'

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

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/user/10', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=10',
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


class TestAlterUser(Endpoint):
    """Tests for PUT /user/<id>?... endpoint."""

    method: str = 'put'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_alter_email(self) -> None:
        data = User.from_alias(self.user).to_dict()
        admin = self.get_client(self.admin)
        assert self.put(self.route, client_id=admin.id, email='lara@croft.io') == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'user': {**data, 'email': 'lara@croft.io'}}})
        assert self.put(self.route, client_id=admin.id, email=data['email']) == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'user': data}})

    def test_alter_other(self) -> None:
        data = User.from_alias(self.user).to_dict()
        admin = self.get_client(self.admin)
        assert self.put(self.route, client_id=admin.id, user_type='awesome') == (
            STATUS['OK'], {'Status': 'Success',
                           'Response': {'user': {**data, 'data': {**data['data'], 'user_type': 'awesome'}}}})
        assert self.put(self.route, client_id=admin.id, user_type='amateur') == (
            STATUS['OK'], {'Status': 'Success', 'Response': {'user': data}})

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/user/10', client_id=admin.id, email='user@example.com') == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=10',
            }
        )


class TestDeleteUser(Endpoint):
    """Tests for DELETE /user endpoint."""

    route: str = '/user/0'  # NOTE: user_id not important because Endpoint tests don't get to it
    method: str = 'delete'
    admin: str = 'superman'
    user: str = 'tomb_raider'  # NOTE: cannot use 007 as it doesn't exist!

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
        with pytest.raises(User.NotFound):
            User.from_alias('007')
        status, payload = self.post('/user', client_id=client.id, json={
            'first_name': 'James', 'last_name': 'Bond', 'email': 'bond@secret.gov.uk',
            'alias': '007', 'data': {'user_type': 'amateur', 'drink_of_choice': 'martini'}})
        user_id = payload['Response']['user']['id']
        assert status == STATUS['OK']
        assert payload == {
            'Status': 'Success',
            'Response': {'user': {'id': int(user_id)}}
        }
        status, payload = self.delete(f'/user/{user_id}', client_id=client.id)
        assert status == STATUS['OK']
        assert payload == {'Status': 'Success', 'Response': {'user': {'id': user_id}}}
        with pytest.raises(User.NotFound):
            User.from_alias('007')

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/user/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_invalid_parameter(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/user/0', client_id=admin.id, foo='42') == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': 'Unexpected parameter: foo'
            }
        )


class TestGetAllUserFacility(Endpoint):
    """Tests for GET /user/<id>/facility endpoints."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}/facility'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.get(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/user/0/facility', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_get_all(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id) == (
            STATUS['OK'],  {
                'Status': 'Success',
                'Response': {
                    'facility': [
                        {
                            'id': 2,
                            'name': 'Croft_1m',
                            'latitude': 51.25,
                            'longitude': -0.41,
                            'elevation': 294.0,
                            'limiting_magnitude': 17.1,
                            'data': {'telescope_design': 'reflector'},
                        },
                        {
                            'id': 3,
                            'name': 'Croft_4m',
                            'latitude': -24.5,
                            'longitude': -69.25,
                            'elevation': 5050.0,
                            'limiting_magnitude': 17.5,
                            'data': {'telescope_design': 'reflector'},
                        },
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


class TestGetOneUserFacility(Endpoint):
    """Tests for GET /user/<id>/facility/<id> endpoints."""

    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}/facility/2'

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
                    'facility': {
                        'id': 2,
                        'name': 'Croft_1m',
                        'latitude': 51.25,
                        'longitude': -0.41,
                        'elevation': 294.0,
                        'limiting_magnitude': 17.1,
                        'data': {'telescope_design': 'reflector'},
                    }
                }
            }
        )

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/user/0/facility/1', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get('/user/3/facility/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'Facility (0) not associated with user (3)',
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


class TestAddUserFacility(Endpoint):
    """Tests for PUT /user/<id>/facility/<id> endpoints."""

    method: str = 'put'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}/facility/4'

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
                'Message': 'Facility (4) not associated with user (3)', })
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
                'Message': 'Facility (4) not associated with user (3)', })

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/user/0/facility/1', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.put('/user/3/facility/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
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


class TestRemoveUserFacility(Endpoint):
    """Tests for DELETE /user/<id>/facility/<id> endpoints."""

    method: str = 'delete'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @property
    def route(self) -> str:
        user_id = User.from_alias(self.user).id
        return f'/user/{user_id}/facility/4'

    def test_permission_denied(self) -> None:
        client = self.get_client(self.user)
        assert self.delete(self.route, client_id=client.id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient',
            }
        )

    # NOTE: See TestAddUserFacility.test_put for successful delete

    def test_user_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/user/0/facility/1', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No user with id=0',
            }
        )

    def test_facility_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.delete('/user/3/facility/0', client_id=admin.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No facility with id=0',
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
