# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for database url model."""


# standard libs
import os

# external libs
import pytest
from hypothesis import given, strategies as st
from cmdkit.config import Namespace

# internal libs
from refitt.database.url import DatabaseURL


@pytest.mark.unit
class TestDatabaseURL:
    """Unit tests for DatabaseURL interface."""

    @staticmethod
    def build(**fields) -> str:
        """Construct instance and return encoding."""
        return DatabaseURL(**fields).encode()

    @staticmethod
    def build_from_namespace(**fields) -> str:
        """Construct instance and return encoding from Namespace."""
        return DatabaseURL.from_namespace(Namespace(**fields)).encode()

    def test_missing_provider(self) -> None:
        """Test raises on 'provider' not given."""
        try:
            self.build()
        except AttributeError as error:
            response, = error.args
            assert response == 'Missing \'provider\''
        else:
            raise AssertionError('Should raise AttributeError')

    @given(provider=st.sampled_from(['postgres', 'timescale']),
           database=st.sampled_from(['one', 'two', 'three']))
    def test_basic(self, provider: str, database: str) -> None:
        """Test simple direct initialization."""
        assert f'{provider}:///{database}' == self.build(provider=provider, database=database)

    def test_file_for_sqlite(self) -> None:
        """Use 'file' for SQLite."""
        filepath = 'some/file/path.db'
        assert f'sqlite:///{filepath}' == self.build(provider='sqlite', file=filepath)

    def test_database_for_sqlite(self) -> None:
        """Use 'database' for SQLite."""
        database = 'some/file/path.db'
        assert f'sqlite:///{database}' == self.build(provider='sqlite', database=database)

    def test_missing_file_and_database_for_sqlite(self) -> None:
        """Either 'file' or 'database' must be provided for SQLite."""
        try:
            self.build(provider='sqlite')
        except AttributeError as error:
            response, = error.args
            assert response == 'Must provide \'file\' for SQLite'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_both_file_and_database_for_sqlite(self) -> None:
        """Test raises on both 'file' and 'database' specified."""
        try:
            self.build(provider='sqlite', database='foo', file='some/file/path.db')
        except AttributeError as error:
            response, = error.args
            assert response == 'Must provide either \'file\' or \'database\' for SQLite'
        else:
            raise AssertionError('Should raise AttributeError')

    @given(field=st.sampled_from(['user', 'password', 'host', 'port']))
    def test_given_invalid_field_for_sqlite(self, field: str) -> None:
        """Test raises on extra field (e.g., 'host') for SQLite."""
        try:
            self.build(provider='sqlite', file='some/file/path.db', **{field: 'any'})
        except AttributeError as error:
            response, = error.args
            assert response == f'Cannot provide \'{field}\' for SQLite'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_given_host(self) -> None:
        """Test with only a hostname."""
        assert 'postgresql://localhost/database' == self.build(
            provider='postgresql', database='database', host='localhost')

    def test_given_host_and_port(self) -> None:
        """Test with a hostname and port number."""
        assert 'postgresql://localhost:1234/database' == self.build(
            provider='postgresql', database='database', host='localhost', port=1234)

    def test_given_host_and_port_and_user_and_password(self) -> None:
        """Test with a hostname, port number, username, and password."""
        assert 'postgresql://bobby:abc@localhost:1234/database' == self.build(
            provider='postgresql', database='database', host='localhost', port=1234, user='bobby', password='abc')

    def test_missing_password(self) -> None:
        """Test raises on missing password for given username."""
        try:
            self.build(provider='postgresql', database='foo', user='bobby')
        except AttributeError as error:
            response, = error.args
            assert response == 'Must provide \'password\' if \'user\' provided'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_missing_username(self) -> None:
        """Test raises on missing username for given password."""
        try:
            self.build(provider='postgresql', database='foo', password='bobby-rocks')
        except AttributeError as error:
            response, = error.args
            assert response == 'Must provide \'user\' if \'password\' provided'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_given_file_for_non_sqlite(self) -> None:
        """Test raises on 'file' given for non-SQLite database."""
        try:
            self.build(provider='postgresql', file='some/file/path.db')
        except AttributeError as error:
            response, = error.args
            assert response == 'Cannot provide \'file\' if not SQLite'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_missing_database_for_non_sqlite(self) -> None:
        """Test raises on 'database' not given for non-SQLite database."""
        try:
            self.build(provider='postgresql')
        except AttributeError as error:
            response, = error.args
            assert response == 'Must provide \'database\' if not SQLite'
        else:
            raise AssertionError('Should raise AttributeError')

    def test_repr(self) -> None:
        """Test basic case for repr."""
        assert (repr(DatabaseURL(provider='postgres', database='foo'))
                == '<DatabaseURL(provider=\'postgres\', database=\'foo\')>')

    def test_repr_with_password(self) -> None:
        """Test password is masked for repr."""
        assert (repr(DatabaseURL(provider='postgres', database='foo', user='bobby', password='abc'))
                == '<DatabaseURL(provider=\'postgres\', database=\'foo\', user=\'bobby\', password=\'****\')>')

    def test_extra_fields(self) -> None:
        """Test url encoding of extra fields."""
        assert 'postgres:///foo?encoding=utf-8' == self.build(provider='postgres', database='foo', encoding='utf-8')

    def test_multiple_extra_fields(self) -> None:
        """Test url encoding of more than one extra fields."""
        assert 'postgres:///foo?encoding=utf-8&other=2' == self.build(
            provider='postgres', database='foo', encoding='utf-8', other=2)

    def test_from_namespace(self) -> None:
        """Test creation from a Namespace."""
        assert 'postgres:///foo?encoding=utf-8' == self.build_from_namespace(
            provider='postgres', database='foo', encoding='utf-8')

    def test_from_namespace_with_env(self) -> None:
        """Test field defined with _env special behavior."""
        os.environ['PASSWORD'] = 'my-password'
        assert 'postgres://bobby:my-password@localhost/foo?encoding=utf-8' == self.build_from_namespace(
            provider='postgres', database='foo', user='bobby', password_env='PASSWORD', encoding='utf-8')

    def test_from_namespace_with_eval(self) -> None:
        """Test field defined with _eval special behavior."""
        assert 'postgres://bobby:my-password@localhost/foo?encoding=utf-8' == self.build_from_namespace(
            provider='postgres', database='foo', user='bobby', password_eval='echo my-password', encoding='utf-8')
