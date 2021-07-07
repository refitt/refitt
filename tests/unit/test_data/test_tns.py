# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for TNS interfaces."""


# type annotations
from __future__ import annotations

# external libs
from hypothesis import given, strategies as st
from cmdkit.config import Namespace, ConfigurationError

# internal libs
from refitt.core.schema import SchemaError
from refitt.data.tns import TNSConfig, TNSInterface, TNSNameSearchResult, TNSObjectSearchResult


class TestTNSConfig:
    """Unit tests for TNSConfig interface."""

    def test_creation(self) -> None:
        """Directly initialize from discrete values."""
        instance = TNSConfig(key='abc', bot_id=123, bot_name='MY_BOT')
        assert instance.key == 'abc'
        assert instance.bot_id == 123
        assert instance.bot_name == 'MY_BOT'

    @given(field=st.sampled_from(['key', 'bot_id', 'bot_name']))
    def test_missing_field_from_dict(self, field: str) -> None:
        """Raises SchemaError on missing `field` in dictionary."""
        args = {'key': 'abc', 'bot_id': 123, 'bot_name': 'MY_BOT'}
        args.pop(field)
        try:
            _ = TNSConfig.from_dict(args)
        except SchemaError as error:
            assert str(error) == f'Missing key \'{field}\''
        else:
            raise AssertionError('Expected SchemaError')

    def test_unexpected_field_from_dict(self) -> None:
        """Raises SchemaError on unexpected field in dictionary."""
        args = {'key': 'abc', 'bot_id': 123, 'bot_name': 'MY_BOT', 'foo': 'bar'}
        try:
            _ = TNSConfig.from_dict(args)
        except SchemaError as error:
            assert str(error) == f'Unexpected key \'foo\''
        else:
            raise AssertionError('Expected SchemaError')

    @given(field=st.sampled_from(['key', 'bot_id', 'bot_name']))
    def test_missing_field_from_config(self, field: str) -> None:
        """Raises ConfigurationError on missing `field` in namespace."""
        args = Namespace({'key': 'abc', 'bot_id': 123, 'bot_name': 'MY_BOT'})
        args.pop(field)
        try:
            _ = TNSConfig.from_config(args)
        except ConfigurationError as error:
            assert str(error) == f'Missing key \'{field}\''
        else:
            raise AssertionError('Expected ConfigurationError')

    def test_unexpected_field_from_config(self) -> None:
        """Raises ConfigurationError on unexpected field in dictionary."""
        args = Namespace({'key': 'abc', 'bot_id': 123, 'bot_name': 'MY_BOT', 'foo': 'bar'})
        try:
            _ = TNSConfig.from_config(args)
        except ConfigurationError as error:
            assert str(error) == f'Unexpected key \'foo\''
        else:
            raise AssertionError('Expected ConfigurationError')

    def test_headers(self) -> None:
        """Request headers are formatted with appropriate values."""
        instance = TNSConfig(key='abc', bot_id=123, bot_name='MY_BOT')
        assert instance.headers == {'User-Agent': f'tns_marker{{"tns_id":{instance.bot_id}, "type":"bot", '
                                                  f'"name":"{instance.bot_name}"}}'}

    def test_format_data(self) -> None:
        """Search data formatted properly with `parameters`."""
        instance = TNSConfig(key='abc', bot_id=123, bot_name='MY_BOT')
        assert instance.format_data(a='foo', b=1, c=42) == {
            'api_key': 'abc', 'data': '{"a": "foo", "b": 1, "c": 42}'
        }


FAKE_TNS_ZTF_ID = 'ZTF21abcdef'
FAKE_TNS_IAU_NAME = '2021abc'
FAKE_TNS_OBJ_ID = 12345
FAKE_TNS_TYPE_NAME = 'SN Ia'
FAKE_TNS_REDSHIFT = 0.123


FAKE_TNS_NAME_DATA = {
    'id_code': 200,
    'id_message': 'Success',
    'data': {
        'received_data': {'internal_name': FAKE_TNS_ZTF_ID},
        'reply': [
            {'objname': FAKE_TNS_IAU_NAME,
             'prefix': 'SN',
             'objid': FAKE_TNS_OBJ_ID}
        ]
    }
}


FAKE_TNS_OBJECT_DATA = {
    'id_code': 200,
    'id_message': 'Success',
    'data': {
        'received_data': {'objname': FAKE_TNS_IAU_NAME},
        'reply': {
            'object_type': {'id': 12, 'name': FAKE_TNS_TYPE_NAME},
            'redshift': FAKE_TNS_REDSHIFT,
        }
    }
}


class MockTNSInterface(TNSInterface):
    """Mock the interface and return fake responses."""

    def __init__(self) -> None:
        super().__init__(TNSConfig(key='abc', bot_id=123, bot_name='REFITT'))

    @property
    def canned_responses(self) -> dict:
        return {'name': FAKE_TNS_NAME_DATA, 'object': FAKE_TNS_OBJECT_DATA}

    def query(self, endpoint: str, **parameters) -> dict:
        """Fake query."""
        return self.canned_responses.get(endpoint)


class TestTNSNameSearchResult:
    """Unit tests for TNSNameSearchResult."""

    def test_initialization(self) -> None:
        """Created object returns instance of type with data."""
        instance = TNSNameSearchResult(FAKE_TNS_NAME_DATA)
        assert isinstance(instance, TNSNameSearchResult)
        assert instance._data == FAKE_TNS_NAME_DATA

    def test_schema_valid(self) -> None:
        """Valid schema provides for properties."""
        instance = TNSNameSearchResult.from_dict(FAKE_TNS_NAME_DATA)
        assert isinstance(instance, TNSNameSearchResult)
        assert instance._data == FAKE_TNS_NAME_DATA
        assert instance.objid == FAKE_TNS_OBJ_ID
        assert instance.prefix == 'SN'
        assert instance.objname == FAKE_TNS_IAU_NAME


class TestTNSObjectSearchResult:
    """Unit tests for TNSObjectSearchResult."""

    def test_initialization(self) -> None:
        """Created object returns instance of type with data."""
        instance = TNSObjectSearchResult(FAKE_TNS_OBJECT_DATA)
        assert isinstance(instance, TNSObjectSearchResult)
        assert instance._data == FAKE_TNS_OBJECT_DATA

    def test_schema_valid(self) -> None:
        """Valid schema provides for properties."""
        instance = TNSObjectSearchResult.from_dict(FAKE_TNS_OBJECT_DATA)
        assert isinstance(instance, TNSObjectSearchResult)
        assert instance._data == FAKE_TNS_OBJECT_DATA
        assert instance.object_type_name == FAKE_TNS_TYPE_NAME
        assert instance.redshift == FAKE_TNS_REDSHIFT

