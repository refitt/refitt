# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for model endpoints."""


# external libs
from pytest import mark

# internal libs
from refitt.database.model import Recommendation, Model, User
from refitt.web.api.response import STATUS, RESPONSE_MAP, NotFound, ParameterInvalid, PermissionDenied, PayloadTooLarge
from tests.integration.test_web.test_api.test_endpoint import Endpoint


@mark.integration
class TestGetModel(Endpoint):
    """Tests for model endpoint."""

    route: str = '/model'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @mark.parametrize('key', ['foo', 'bar', 'baz'])
    @mark.parametrize('value', ['0', '3.14', 'false', 'null'])
    def test_invalid_parameter(self, key: str, value: str) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, **{key: value, }) == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': f'Unexpected parameter: {key}'
            }
        )

    def test_missing_parameters(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': 'Cannot query models without \'epoch_id\' or \'object_id\' and without \'limit\''
            }
        )

    @mark.parametrize('key', ['epoch_id', 'object_id'])
    def test_missing_limit_on_included_data(self, key: str) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        include_data='true', **{key: '3'}) == (
            RESPONSE_MAP[PayloadTooLarge], {
                'Status': 'Error',
                'Message': 'Cannot include full model data without \'limit\''
            }
        )

    @mark.parametrize('key', ['epoch_id', 'type_id', 'object_id', 'limit'])
    @mark.parametrize('value', ['3.14', 'null', 'false', 'abc'])
    def test_invalid_parameter_type(self, key: str, value: str) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id, **{key: value}) == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': f'Expected integer for {key} (given {value})'
            }
        )

    def test_permission_denied(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id, epoch_id='3') == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Authorization level insufficient'
            }
        )

    def test_by_epoch(self) -> None:
        models = [model.to_json() for model in Model.query().filter_by(epoch_id=3).all()]
        for model in models:
            model.pop('data')
        assert len(models) == 8
        assert self.get(self.route, client_id=self.get_client(self.admin).id, epoch_id='3') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': models}},
        )

    def test_by_epoch_include_data(self) -> None:
        models = [model.to_json() for model in Model.query().filter_by(epoch_id=3).all()]
        assert len(models) == 8
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        epoch_id='3', include_data='true', limit='10') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': models}},
        )

    def test_by_object(self) -> None:
        models = [model.to_json() for model in Model.from_object(8)]
        for model in models:
            model.pop('data')
        assert len(models) == 3
        assert self.get(self.route, client_id=self.get_client(self.admin).id, object_id='8') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': models}},
        )

    def test_by_object_include_data(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        object_id='8', include_data='true', limit='10') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': [model.to_json() for model in Model.from_object(8)]}},
        )

    def test_by_type_1(self) -> None:
        models = [model.to_json() for model in Model.query().filter_by(type_id=1)]
        for model in models:
            model.pop('data')
        assert len(models) == 24
        assert self.get(self.route, client_id=self.get_client(self.admin).id, type_id='1', limit='100') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': models}},
        )

    def test_by_type_2(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id, type_id='2', limit='100') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': []}},
        )

    def test_by_type_include_data(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.admin).id,
                        type_id='1', include_data='true', limit='100') == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': [model.to_json() for model in Model.query().filter_by(type_id=1).all()]}},
        )


@mark.integration
class TestGetModelByID(Endpoint):
    """Tests for model endpoint."""

    route: str = '/model/8'
    method: str = 'get'
    admin: str = 'superman'
    user: str = 'tomb_raider'

    @mark.parametrize('key', ['foo', 'bar', 'baz'])
    @mark.parametrize('value', ['0', '3.14', 'false', 'null'])
    def test_invalid_parameter(self, key: str, value: str) -> None:
        admin = self.get_client(self.admin)
        assert self.get(self.route, client_id=admin.id, **{key: value, }) == (
            RESPONSE_MAP[ParameterInvalid], {
                'Status': 'Error',
                'Message': f'Unexpected parameter: {key}'
            }
        )

    @mark.parametrize('value', ['abc', 'false', 'null', '3.14'])
    def test_id_not_integer(self, value: str) -> None:
        admin = self.get_client(self.admin)
        assert self.get(f'/model/{value}', client_id=admin.id,) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': f'Not found: /model/{value}'
            }
        )

    def test_permission_denied(self) -> None:
        assert self.get(self.route, client_id=self.get_client(self.user).id) == (
            RESPONSE_MAP[PermissionDenied], {
                'Status': 'Error',
                'Message': 'Model is not public'
            }
        )

    def test_not_found(self) -> None:
        admin = self.get_client(self.admin)
        assert self.get(f'/model/0', client_id=admin.id,) == (
            RESPONSE_MAP[NotFound], {
                'Status': 'Error',
                'Message': f'No model with id=0'
            }
        )

    def test_success(self) -> None:
        user_id = User.from_alias(self.user).id
        recommendation = Recommendation.query().filter_by(user_id=user_id).first()
        model = Model.query().filter_by(observation_id=recommendation.predicted_observation_id).first()
        assert self.get(f'/model/{model.id}', client_id=self.get_client(self.user).id) == (
            STATUS['OK'], {
                'Status': 'Success',
                'Response': {'model': model.to_json(), }}
        )
