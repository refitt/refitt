# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""DatabaseURL implementation."""


# type annotations
from __future__ import annotations
from typing import Any

# standard libs
from urllib.parse import urlencode

# external libs
from cmdkit.config import Namespace

# public interface
__all__ = ['DatabaseURL', ]


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


class DatabaseURL(dict):
    """
    Namespace-like representation for defining database connection URL.
    Standard arguments apply. Extra arguments are encoded as URL parameters.

    Example:
        >>> url = DatabaseURL(provider='postgresql', database='mine', encoding='utf-8')
        >>> url.encode()
        'postgresql://localhost/mine?encoding=utf-8'
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
                             parameters=fields)
        except KeyError as error:
            raise AttributeError('Missing \'provider\'') from error
        self.__validate()

    def __getattr__(self, field: str) -> Any:
        return self.get(field)

    def __repr__(self) -> str:
        """Interactive representation."""
        masked = self.__class__(**self)
        masked['password'] = None if self.password is None else '****'
        value = '<DatabaseURL('
        value += ', '.join([field + '=' + repr(masked.get(field))
                            for field in ('provider', 'database', 'file', 'user', 'password', 'host', 'port')
                            if masked.get(field) is not None])
        if self.parameters:
            value += ', ' + ', '.join([field + '=' + repr(value)
                                       for field, value in self.parameters.items()])
        return value + ')>'

    def __validate(self) -> None:
        """Check validity of provided fields during initialization."""
        if self.provider == 'sqlite':
            self.__validate_sqlite()
        else:
            self.__validate_database()
            self.__validate_user_and_password()

    def __validate_user_and_password(self) -> None:
        """Check that username and password are valid."""
        if self.user is not None and self.password is None:
            raise AttributeError('Must provide \'password\' if \'user\' provided')
        if self.user is None and self.password is not None:
            raise AttributeError('Must provide \'user\' if \'password\' provided')

    def __validate_sqlite(self) -> None:
        """Check necessary and unambiguous for SQLite provider."""
        if self.file is None and self.database is None:
            raise AttributeError('Must provide \'file\' for SQLite')
        if self.file is not None and self.database is not None:
            raise AttributeError('Must provide either \'file\' or \'database\' for SQLite')
        for field in ('user', 'password', 'host', 'port'):
            if self.get(field) is not None:
                raise AttributeError(f'Cannot provide \'{field}\' for SQLite')

    def __validate_database(self) -> None:
        """Check necessary and unambiguous for non-SQLite provider."""
        if self.file:
            raise AttributeError('Cannot provide \'file\' if not SQLite')
        if not self.database:
            raise AttributeError('Must provide \'database\' if not SQLite')

    def encode(self) -> str:
        """Construct URL string with encoded parameters."""
        return ''.join([
            f'{self.provider}://',
            self.__format_user_and_password(),
            self.__format_host_and_port(),
            self.__format_database_or_file(),
            self.__format_parameters(),
        ])

    def __format_parameters(self) -> str:
        """Build formatted sub-string for url-parameters."""
        return '' if not self.parameters else '?' + urlencode(self.parameters)

    def __format_database_or_file(self) -> str:
        """Build formatted sub-string for database name/path."""
        return f'/{self.file}' if not self.database else f'/{self.database}'

    def __format_host_and_port(self) -> str:
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

    def __format_user_and_password(self) -> str:
        """Build formatted sub-string for user name and password."""
        return '' if not self.user and not self.password else f'{self.user}:{self.password}@'

    def __str__(self) -> str:
        return self.encode()

    @classmethod
    def from_namespace(cls, ns: Namespace) -> DatabaseURL:
        fields = {}
        for key in ns.keys():
            name = _strip_endings_from_string(key, '_env', '_eval')
            fields[name] = getattr(ns, name)
        return cls(**fields)
