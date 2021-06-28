# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for TNS interfaces."""


# external libs
from hypothesis import given, strategies as st
from cmdkit.config import Namespace, ConfigurationError

# internal libs
from refitt.core.schema import SchemaError
from refitt.data.tns import TNSConfig


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
