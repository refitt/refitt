# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core database tools."""


# type annotations
from __future__ import annotations
from typing import Any, TypeVar, Dict, List, Union, Callable

# standard libs
from datetime import datetime
from urllib.parse import urlencode
from base64 import decodebytes as base64_decode, encodebytes as base64_encode

# external libs
from cmdkit.config import Namespace
from sqlalchemy.exc import NoResultFound, MultipleResultsFound

# public interface
__all__ = [
    'DatabaseConfiguration',
    'DatabaseError', 'NotFound', 'NotDistinct', 'AlreadyExists',
    '_load', '_dump',  # internal
]


def _strip_endings_from_string(value: str, *endings: str) -> str:
    """
    Removing instances of each possible `endings` from `value`.

    Example:
        >>> _strip_endings_from_string('some_env', '_env', '_eval')
        'some'
    """
    result = str(value)
    for ending in endings:
        pos = len(ending)
        if result[-pos:] == ending:
            result = result[:-pos]
    return result


class DatabaseConfiguration(Namespace):
    """
    Namespace-like representation for defining database connection details.
    Standard arguments apply. Extra arguments are encoded as URL parameters.

    Example:
        >>> url = DatabaseConfiguration(provider='postgresql', database='mine', encoding='utf-8')
        >>> url.encode()
        'postgresql:///mine?encoding=utf-8'
    """

    def __init__(self, **fields) -> None:
        """Direct initialize by `fields`."""
        try:
            super().__init__(provider=fields.pop('provider'),
                             database=fields.pop('database', None),
                             file=fields.pop('file', None),
                             user=fields.pop('user', None),
                             password=fields.pop('password', None),
                             host=fields.pop('host', None),
                             port=fields.pop('port', None),
                             schema=fields.pop('schema', None),
                             echo=fields.pop('echo', False),
                             connect_args=fields.pop('connect_args', {}),
                             parameters=fields)
        except KeyError as error:
            raise AttributeError('Missing \'provider\'') from error
        else:
            if self.provider == 'sqlite':
                self.__validate_sqlite()
            else:
                self.__validate_database()
                self.__validate_user_and_password()

    def __repr__(self: DatabaseConfiguration) -> str:
        """Interactive representation."""
        masked = self.to_dict()
        masked['password'] = None if self.password is None else '****'
        parameters = masked.pop('parameters')
        value = f'<{self.__class__.__name__}('
        value += ', '.join([field + '=' + repr(value) for field, value in masked.items() if value])
        if parameters:
            value += ', ' + ', '.join([field + '=' + repr(value) for field, value in parameters.items() if value])
        return value + ')>'

    def __validate_user_and_password(self: DatabaseConfiguration) -> None:
        """Check that username and password are valid."""
        if self.user is not None and self.password is None:
            raise AttributeError('Must provide \'password\' if \'user\' provided')
        if self.user is None and self.password is not None:
            raise AttributeError('Must provide \'user\' if \'password\' provided')

    def __validate_sqlite(self: DatabaseConfiguration) -> None:
        """Check necessary and unambiguous for SQLite provider."""
        if self.file is None and self.database is None:
            raise AttributeError('Must provide \'file\' for SQLite')
        if self.file is not None and self.database is not None:
            raise AttributeError('Must provide either \'file\' or \'database\' for SQLite')
        for field in ('user', 'password', 'host', 'port'):
            if self.get(field) is not None:
                raise AttributeError(f'Cannot provide \'{field}\' for SQLite')

    def __validate_database(self: DatabaseConfiguration) -> None:
        """Check necessary and unambiguous for non-SQLite provider."""
        if self.file:
            raise AttributeError('Cannot provide \'file\' if not SQLite')
        if not self.database:
            raise AttributeError('Must provide \'database\' if not SQLite')

    def encode(self: DatabaseConfiguration) -> str:
        """Construct URL string with encoded parameters."""
        return ''.join([
            f'{self.provider}://',
            self.__format_user_and_password(),
            self.__format_host_and_port(),
            self.__format_database_or_file(),
            self.__format_parameters(),
        ])

    def __format_parameters(self: DatabaseConfiguration) -> str:
        """Build formatted sub-string for url-parameters."""
        return '' if not self.parameters else '?' + urlencode(self.parameters)

    def __format_database_or_file(self: DatabaseConfiguration) -> str:
        """Build formatted sub-string for database name/path."""
        return f'/{self.file}' if not self.database else f'/{self.database}'

    def __format_host_and_port(self: DatabaseConfiguration) -> str:
        """Build formatted sub-string for host name and port number."""
        if self.host and self.port:
            return f'{self.host}:{self.port}'
        elif self.host and not self.port:
            return f'{self.host}'
        elif self.port and not self.host:
            return f'localhost:{self.port}'
        else:
            if self.user or self.password:
                return 'localhost'
            else:
                return ''

    def __format_user_and_password(self: DatabaseConfiguration) -> str:
        """Build formatted sub-string for user name and password."""
        return '' if not self.user and not self.password else f'{self.user}:{self.password}@'

    def __str__(self: DatabaseConfiguration) -> str:
        """String representation is the encoded URL."""
        return self.encode()

    @classmethod
    def from_namespace(cls, ns: Namespace) -> DatabaseConfiguration:
        """Construct from existing namespace."""
        fields = {}
        for key in ns.keys():
            name = _strip_endings_from_string(key, '_env', '_eval')
            fields[name] = getattr(ns, name)
        return cls(**fields)


class DatabaseError(Exception):
    """Generic error with respect to the database model."""


class NotFound(NoResultFound):
    """Exception specific to no record found on lookup by unique field (e.g., `id`)."""


class NotDistinct(MultipleResultsFound):
    """Exception specific to multiple records found when only one should have been."""


class AlreadyExists(DatabaseError):
    """Exception specific to a record with unique properties already existing."""


__NT = type(None)
__VT = TypeVar('__VT', __NT, bool, int, float, str, Dict[str, Any], List[str])
__RT = Union[__VT, datetime, bytes]


def __load_datetime(value: __VT) -> Union[__VT, datetime]:
    """Passively coerce datetime formatted strings into actual datetime values."""
    if not isinstance(value, str):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        return value


def __dump_datetime(value: __RT) -> __VT:
    """Passively coerce datetime values to formatted strings."""
    if not isinstance(value, datetime):
        return value
    else:
        return str(value)


def __load_bytes(value: __VT) -> Union[__VT, bytes]:
    """Passively coerce string lists (base64 encoded raw data)."""
    if isinstance(value, list) and all(isinstance(member, str) for member in value):
        return base64_decode('\n'.join(value).encode())
    else:
        return value


def __dump_bytes(value: __RT) -> __VT:
    """Passively coerce bytes into base64 encoded string sets."""
    if not isinstance(value, bytes):
        return value
    else:
        return base64_encode(value).decode().strip().split('\n')


__LM = Callable[[__VT], __RT]
__DM = Callable[[__RT], __VT]
__loaders: List[__LM] = [__load_datetime, __load_bytes, ]
__dumpers: List[__DM] = [__dump_datetime, __dump_bytes, ]


def __load_imp(value: __VT, filters: List[__LM]) -> __RT:
    return value if not filters else filters[0](__load_imp(value, filters[1:]))


def _load(value: __VT) -> __RT:
    """Passively coerce value types of stored record assets to db compatible types."""
    return __load_imp(value, __loaders)


def __dump_imp(value: __RT, filters: List[__DM]) -> __VT:
    return value if not filters else filters[0](__dump_imp(value, filters[1:]))


def _dump(value: __RT) -> __VT:
    """Passively coerce db types to JSON encoded types."""
    return __dump_imp(value, __dumpers)
