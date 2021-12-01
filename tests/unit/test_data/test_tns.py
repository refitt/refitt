# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for TNS interfaces."""


# type annotations
from __future__ import annotations
from typing import Union

# standard libs
import json
import functools
from io import BytesIO
from datetime import timedelta

# external libs
import pytest
from hypothesis import given, strategies as st
from cmdkit.config import Namespace, ConfigurationError
from pandas import DataFrame
from requests import Response

# internal libs
from refitt.core import base64
from refitt.core.schema import SchemaError
from refitt.data.tns.catalog import TNSCatalog, TNSRecord
from refitt.data.tns.interface import (TNSConfig, TNSInterface,
                                       TNSNameSearchResult, TNSObjectSearchResult, TNSQueryCatalogResult)


@pytest.mark.unit
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


FAKE_TNS_CATALOG_DATA = """\
UEsDBBQAAAAIABt2aFO5G34tdwIAANMIAAAWABwAdG5zX3B1YmxpY19vYmplY3RzLmNzdlVUCQAD
JX+JYSV/iWF1eAsAAQT1AQAABBQAAADtlN9P2zAQx9/5Kyz2MJCuVvwjcZK3wgaMHxKjTGhPyDRO
6il1OsdtKX/9LqGMDvqCxN6IItn3Pft8vo/tT2TaFLa0psgJjzgbMDZICZO5THPGd5q7X7YAp6fm
duZNae/7PngNhRnX1ulgGwfeFO3ElgHCamZwfNegOGt8sK66rXwzn6H8QoG2mfux+eveNKGw7bhZ
GL8qdDDP1lRXvYFtaetgPKybx9jGtxAsJuvN2NiFKcA6FJ2ub7u8Wxh706fcR611G552v5PFqUpg
eA1dFXSxfAAhaZywTImYcw4so4lkgkUqSzLAT8KldoPR9fDqasReWE+VjBhhLJdxLhIaRRFwRjMO
HA1Ywu4ZJYf4T/T0rkucXFNSGHLQ4HbIKSUH87pad4+09TUOA3JBycn8rpMP6QBnn1vXTzxvlgbI
V0oudOVs5x9SMhpP5nV4AHJFuyg32jqsow5ATig51g3Z+1YOgfxwWCrf2rAiTUlO9FJbuw8E07vB
GFMbJkC+0C7Iz2buqj6jY1vX2hV93iMc5e0Cq6kXfYZHuCoei85x2kXQPoTHYXZK9r7PjXGf281l
D0xd4vT9fh3cxI231SSQvX8zu7DOmbYJen/3ucKKcJHLLBcCLkec1at2i09u03rk8QbyFQhBeYqi
SiVPgCkaRxmTSarEW5HLPMIDs0aefSD/H8iZWiP3W3zpNq1HLjeQ34OIU6qUUEnKWXfJBXZ4IiLx
BuBRjG9lzlOaPgLn6Qfw9wee5nG2Bv77Ndyu8q+1HrjYAL4Eic+6UJyhjR6845lSsVRJlLK33fFY
5kxS2S3MqVAfyN8fucrl07M+2+J79ax32s4fUEsBAh4DFAAAAAgAG3ZoU7kbfi13AgAA0wgAABYA
GAAAAAAAAQAAAKSBAAAAAHRuc19wdWJsaWNfb2JqZWN0cy5jc3ZVVAUAAyV/iWF1eAsAAQT1AQAA
BBQAAABQSwUGAAAAAAEAAQBcAAAAxwIAAAAA
"""


class TNSResponseStub(Response):
    """A stub of a response holding fake data explicitly defined for the tests."""

    fake_data = {
        'name': FAKE_TNS_NAME_DATA,
        'object': FAKE_TNS_OBJECT_DATA,
        'catalog': FAKE_TNS_CATALOG_DATA,
    }

    @classmethod
    def build(cls, endpoint: str) -> TNSResponseStub:
        """Build response with data based on `endpoint`."""
        return cls.__build(cls.fake_data.get(endpoint))

    @classmethod
    def __build(cls, data: Union[dict, str], status_code: int = 200) -> TNSResponseStub:
        """Prepare response with `data` content."""
        r = cls()
        if isinstance(data, str):
            r._content = base64.decode(data)
        else:
            r._content = json.dumps(data).encode()
        r.status_code = status_code
        return r


class MockTNSInterface(TNSInterface):
    """Mock the interface and return fake responses."""

    def __init__(self) -> None:
        super().__init__(TNSConfig(key='abc', bot_id=123, bot_name='REFITT'))

    def query(self, endpoint: str, **parameters) -> TNSResponseStub:
        """Fake query."""
        return TNSResponseStub.build(endpoint)


@pytest.mark.unit
class TestTNSNameSearchResult:
    """Unit tests for TNSNameSearchResult."""

    def test_initialization(self) -> None:
        """Created object returns instance of type with data."""
        instance = TNSNameSearchResult.from_dict(FAKE_TNS_NAME_DATA)
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestTNSCatalogSearchResult:
    """Unit tests for TNSCatalogSearchResult."""

    def test_initialization(self) -> None:
        """Created object returns instance of type with data."""
        data = base64.decode(FAKE_TNS_CATALOG_DATA)
        instance = TNSQueryCatalogResult(data)
        assert isinstance(instance, TNSQueryCatalogResult)
        assert instance.data == instance._data == data


class MockTNSCatalog(TNSCatalog):
    """A TNSCatalog with a mocked interface to return fake data."""

    interface = MockTNSInterface

    def refresh(self, expired_after: timedelta = TNSCatalog.DEFAULT_EXPIRED_AFTER) -> MockTNSCatalog:
        """No caching behavior, returns self."""
        return self


@pytest.mark.unit
class TestTNSCatalog:
    """Unit tests for TNSCatalog."""

    @functools.cached_property
    def data(self) -> DataFrame:
        """Load dataframe only once."""
        return TNSCatalog.from_zip(BytesIO(base64.decode(FAKE_TNS_CATALOG_DATA))).data

    def test_init(self) -> None:
        """Direct initialization with a `pandas.DataFrame`."""
        catalog = TNSCatalog(self.data)
        assert isinstance(catalog, TNSCatalog)
        assert isinstance(catalog.data, DataFrame)
        assert isinstance(TNSCatalog(catalog), TNSCatalog)

    def test_from_local(self) -> None:
        """Initialize from extract CSV file."""
        catalog = TNSCatalog.from_local(BytesIO(self.data.to_csv(index=False).encode()))
        assert isinstance(catalog, TNSCatalog)
        assert catalog.data.equals(self.data)

    def test_from_zip(self) -> None:
        """Initialize from raw Zip archive."""
        catalog = TNSCatalog.from_zip(BytesIO(base64.decode(FAKE_TNS_CATALOG_DATA)))
        assert isinstance(catalog, TNSCatalog)
        assert catalog.data.equals(self.data)

    def test_from_query(self) -> None:
        """Initialize from prepared response."""
        response = TNSResponseStub.build('catalog')
        result = TNSQueryCatalogResult.from_response(response)
        catalog = TNSCatalog.from_query(result)
        assert isinstance(catalog, TNSCatalog)
        assert catalog.data.equals(self.data)

    def test_from_web(self) -> None:
        """Initialize via web query (using mocked interface)."""
        catalog = MockTNSCatalog.from_web(cache=False)
        assert isinstance(catalog, TNSCatalog)
        assert catalog.data.equals(self.data)

    def test_get(self) -> None:
        """Look up records by name."""
        catalog = TNSCatalog(self.data)
        for name in catalog.data.name:
            record = catalog.get(name)
            assert isinstance(record, TNSRecord)
            assert record.name == name

    def test_no_record_found_unrecognized_name(self) -> None:
        """Exception is raised if object not found in catalog."""
        catalog = TNSCatalog(self.data)
        try:
            catalog.get('foobar')
        except TNSCatalog.NoRecordsFound as error:
            message, = error.args
            assert message == 'Unrecognized name pattern \'foobar\''
        else:
            raise AssertionError('Expected TNSCatalog.NoRecordsFound')

    def test_no_record_found_with_iau(self) -> None:
        """Exception is raised if object not found in catalog."""
        catalog = TNSCatalog(self.data)
        try:
            catalog.get('2021zzz')
        except TNSCatalog.NoRecordsFound as error:
            message, = error.args
            assert message == 'No record with name == 2021zzz'
        else:
            raise AssertionError('Expected TNSCatalog.NoRecordsFound')

    def test_no_record_found_with_other(self) -> None:
        """Exception is raised if object not found in catalog."""
        catalog = TNSCatalog(self.data)
        try:
            catalog.get('ZTF20actresa')
        except TNSCatalog.NoRecordsFound as error:
            message, = error.args
            assert message == 'No record with object_names ~ ZTF20actresa'
        else:
            raise AssertionError('Expected TNSCatalog.NoRecordsFound')

    def test_multiple_records_found(self) -> None:
        """Exception is raised if object not found in catalog."""
        # artificially duplicate names
        data = self.data.copy()
        data.internal_names = data.internal_names.map(lambda names: f'{names}, ZTF20actresa')
        catalog = TNSCatalog(data)
        try:
            catalog.get('ZTF20actresa')
        except TNSCatalog.MultipleRecordsFound as error:
            message, = error.args
            assert message == 'Multiple records with object_names ~ ZTF20actresa'
        else:
            raise AssertionError('Expected TNSCatalog.NoRecordsFound')
