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

"""Integration tests for /observation endpoints."""


# internal libs
from refitt.database.model import Source, Observation, ObservationType, Alert, Forecast, File, FileType
from refitt.web.api.response import STATUS, RESPONSE_MAP, NotFound, ParameterInvalid, PermissionDenied, PayloadTooLarge
from tests.integration.test_web.test_api.test_endpoint import Endpoint


class TestGetObservations(Endpoint):
    """Tests for GET /observation endpoint."""

    route: str = '/observation'
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

    def test_too_few_filters(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': 'Must specify at least one of [\'source_id\', \'object_id\', \'limit\']'
            }
        )

    def test_cannot_query_broker(self) -> None:
        source = Source.from_name('antares')
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        source_id=source.id) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': f'Cannot query all observations for broker (source_id={source.id})'
            }
        )

    def test_query_broker(self) -> None:
        source = Source.from_name('antares')
        observation = Observation.with_source(source.id)[0]
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        source_id=source.id, limit=1, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': [observation.to_json(join=True), ]}},
        )

    def test_query_source(self) -> None:
        source = Source.from_name('tomb_raider_croft_1m')
        observations = Observation.with_source(source.id)
        assert self.get(self.route, client_id=self.get_client(self.admin).id, source_id=source.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': [obs.to_json() for obs in observations]}},
        )

    def test_query_source_not_public(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        assert self.get(self.route, client_id=self.get_client(self.user).id, source_id=source.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': []}},
        )

    def test_query_object(self) -> None:
        observations = Observation.with_object(1)
        assert self.get(self.route, client_id=self.get_client(self.admin).id, object_id=1) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': [obs.to_json() for obs in observations]}},
        )

    def test_query_object_not_public(self) -> None:
        source = Source.from_name('antares')
        observations = Observation.with_object(1)  # NOTE: tomb_raider never recommended #1
        assert self.get(self.route, client_id=self.get_client(self.user).id, object_id=1) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': [obs.to_json() for obs in observations
                                             if obs.source_id == source.id]}},
        )

    def test_query_object_and_source(self) -> None:
        source = Source.from_name('antares')
        observations = Observation.with_object(1)
        assert self.get(self.route, client_id=self.get_client(self.admin).id, source_id=source.id, object_id=1) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': [obs.to_json() for obs in observations
                                             if obs.source_id == source.id]}},
        )


class TestGetObservation(Endpoint):
    """Tests for GET /observation/<id> endpoint."""

    route: str = '/observation/1'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': observation.to_json(join=False)},
            }
        )

    def test_get_by_id_with_join(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}', client_id=client.id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation': observation.to_json(join=True)},
            }
        )


class TestGetObservationObject(Endpoint):
    """Tests for GET /observation/<id>/object endpoint."""

    route: str = '/observation/1/object'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/object', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/object', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/object', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object': observation.object.to_json(join=False)},
            }
        )

    def test_get_by_id_with_join(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/object', client_id=client.id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object': observation.object.to_json(join=True)},
            }
        )


class TestGetObservationObjectType(Endpoint):
    """Tests for GET /observation/<id>/object/type endpoint."""

    route: str = '/observation/1/object/type'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/object/type', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/object/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/object/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'object_type': observation.object.type.to_json(join=False)},
            }
        )


class TestGetObservationType(Endpoint):
    """Tests for GET /observation/<id>/type endpoint."""

    route: str = '/observation/1/type'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/type', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation_type': observation.type.to_json(join=False)},
            }
        )


class TestGetObservationSource(Endpoint):
    """Tests for GET /observation/<id>/source endpoint."""

    route: str = '/observation/1/source'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/source', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/source', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source': observation.source.to_json(join=False)},
            }
        )

    def test_get_by_id_with_join(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/source', client_id=client.id, join=True) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source': observation.source.to_json(join=True)},
            }
        )


class TestGetObservationSourceType(Endpoint):
    """Tests for GET /observation/<id>/source/type endpoint."""

    route: str = '/observation/1/source/type'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source/type', client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/source/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/source/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'source_type': observation.source.type.to_json(join=False)},
            }
        )


class TestGetObservationSourceUser(Endpoint):
    """Tests for GET /observation/<id>/source/user endpoint."""

    route: str = '/observation/1/source/user'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source/user',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/source/user', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        source = Source.from_name('tomb_raider_croft_1m')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source/user',
                        client_id=self.get_client('tomb_raider').id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'user': observation.source.user.to_json(join=False)},
            }
        )


class TestGetObservationSourceFacility(Endpoint):
    """Tests for GET /observation/<id>/source/facility endpoint."""

    route: str = '/observation/1/source/facility'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source/facility',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/source/facility', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        source = Source.from_name('tomb_raider_croft_1m')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/source/facility',
                        client_id=self.get_client('tomb_raider').id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'facility': observation.source.facility.to_json(join=False)},
            }
        )


class TestGetObservationAlert(Endpoint):
    """Tests for GET /observation/<id>/alert endpoint."""

    route: str = '/observation/1/alert'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/alert',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/alert', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_alert_not_found(self) -> None:
        source = Source.from_name('refitt')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/alert',
                        client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': f'No alert with observation_id={observation.id}',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(1)
        assert self.get(f'/observation/{observation.id}/alert', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'alert': Alert.from_observation(observation.id).data},
            }
        )


class TestGetObservationForecast(Endpoint):
    """Tests for GET /observation/<id>/forecast endpoint."""

    route: str = '/observation/10/forecast'
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/forecast',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Observation is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/forecast', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation with id=0',
            }
        )

    def test_forecast_not_found(self) -> None:
        source = Source.from_name('antares')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/forecast',
                        client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': f'No forecast with observation_id={observation.id}',
            }
        )

    def test_get_by_id(self) -> None:
        source = Source.from_name('refitt')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/forecast',
                        client_id=self.get_client(self.admin).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'forecast': Forecast.from_observation(observation.id).data},
            }
        )


class TestGetObservationFile(Endpoint):
    """Tests for GET /observation/<id>/file endpoint."""

    route: str = '/observation/21/file'  # NOTE: first file in test suite for tomb_raider
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/file',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'File is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/file', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with observation_id=0',
            }
        )

    def test_file_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/1/file', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with observation_id=1',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(21)
        assert self.get(f'/observation/{observation.id}/file', client_id=client.id, response_type='bytes') == (
            STATUS['OK'], File.from_observation(observation.id).data
        )


class TestGetObservationFileType(Endpoint):
    """Tests for GET /observation/<id>/file endpoint."""

    route: str = '/observation/21/file/type'  # NOTE: first file in test suite for tomb_raider
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')
        observation = Observation.with_source(source.id)[0]
        assert self.get(f'/observation/{observation.id}/file/type',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'File is not public'
            }
        )

    def test_observation_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/0/file/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with observation_id=0',
            }
        )

    def test_file_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/1/file/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with observation_id=1',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        observation = Observation.from_id(21)
        file_type = File.from_observation(observation.id).type
        assert self.get(f'/observation/{observation.id}/file/type', client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'file_type': file_type.to_json()}}
        )


class TestGetType(Endpoint):
    """Tests for GET /observation/type/<id> endpoint."""

    route: str = '/observation/type/1'
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

    def test_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/type/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No observation_type with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        obs_type = ObservationType.from_id(1)
        assert self.get(f'/observation/type/1', client_id=self.get_client(self.admin).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'observation_type': obs_type.to_json()},
            }
        )


class TestGetAlert(Endpoint):
    """Tests for GET /observation/alert/<id> endpoint."""

    route: str = '/observation/alert/1'
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

    def test_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/alert/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No alert with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        alert = Alert.from_id(1)
        assert self.get(f'/observation/alert/1', client_id=self.get_client(self.admin).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'alert': alert.data},
            }
        )


class TestGetForecast(Endpoint):
    """Tests for GET /observation/forecast/<id> endpoint."""

    route: str = '/observation/forecast/1'
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

    def test_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/forecast/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No forecast with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        forecast = Forecast.from_id(1)
        assert self.get(f'/observation/forecast/1', client_id=self.get_client(self.admin).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'forecast': forecast.data},
            }
        )


class TestGetFileType(Endpoint):
    """Tests for GET /observation/file/type/<id> endpoint."""

    route: str = '/observation/file/type/1'
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

    def test_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/file/type/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file_type with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        file_type = FileType.from_id(1)
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'file_type': file_type.to_json()}}
        )


class TestGetFile(Endpoint):
    """Tests for GET /observation/file/<id> endpoint."""

    route: str = '/observation/file/3'  # NOTE: first file in test suite for tomb_raider
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')  # NOTE: not tomb_raider
        observation = Observation.with_source(source.id)[0]
        file = File.from_observation(observation.id)
        assert self.get(f'/observation/file/{file.id}',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'File is not public'
            }
        )

    def test_file_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/file/0', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        file_id = int(self.route.split('/')[-1])
        file = File.from_id(file_id).to_dict()
        obs_id = file['observation_id']
        assert self.get(self.route, client_id=client.id, response_type='file') == (
            STATUS['OK'], {f'observation_{obs_id}.fits.gz': file['data']}
        )


class TestGetFileTypeForFile(Endpoint):
    """Tests for GET /observation/file/<id>/type endpoint."""

    route: str = '/observation/file/3/type'  # NOTE: first file in test suite for tomb_raider
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

    def test_permission_denied(self) -> None:
        source = Source.from_name('delta_one_bourne_12in')  # NOTE: not tomb_raider
        observation = Observation.with_source(source.id)[0]
        file = File.from_observation(observation.id)
        assert self.get(f'/observation/file/{file.id}/type',
                        client_id=self.get_client('tomb_raider').id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'File is not public'
            }
        )

    def test_file_not_found(self) -> None:
        client = self.get_client(self.user)
        assert self.get(f'/observation/file/0/type', client_id=client.id) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': 'No file with id=0',
            }
        )

    def test_get_by_id(self) -> None:
        client = self.get_client(self.user)
        file_id = int(self.route.split('/')[-2])
        assert self.get(self.route, client_id=client.id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'file_type': File.from_id(file_id).type.to_json()}}
        )
