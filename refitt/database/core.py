# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core interface for database engine and session manager."""


# type annotations
from __future__ import annotations
from typing import Any

# standard libs
import logging
from urllib.parse import urlencode

# external libs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import ArgumentError

# internal libs
from ..core.config import config, Namespace, ConfigurationError

# public interface
__all__ = ['DatabaseURL', 'backends', 'engine', 'Session', 'config', ]


# initialize module level logger
log = logging.getLogger(__name__)


class DatabaseURL(dict):
    """
    Dataclass-like representation for database URL.
    Standard arguments apply. Extra arguments are encoded as URL parameters.

    Example:
        >>> url = DatabaseURL(provider='postgresql', database='mine')
        >>> url.encode()
        'postgresql://localhost/mine'
    """

    def __init__(self, **fields) -> None:
        """Initialize fields."""
        try:
            super().__init__(backend=fields.pop('backend'),
                             database=fields.pop('database', None),
                             file=fields.pop('file', None),
                             user=fields.pop('user', None),
                             password=fields.pop('password', None),
                             host=fields.pop('host', None),
                             port=fields.pop('port', None),
                             parameters=fields)
        except KeyError as _error:
            raise AttributeError('Missing \'backend\'') from _error
        self._validate()

    def __getattr__(self, field: str) -> Any:
        return self.get(field)

    def __repr__(self) -> str:
        """Interactive representation."""
        masked = self.__class__(**self)
        masked['password'] = None if self.password is None else '****'
        value = '<DatabaseURL('
        value += ', '.join([field + '=' + repr(masked.get(field))
                            for field in ('backend', 'database', 'file', 'user', 'password', 'host', 'port')
                            if masked.get(field) is not None])
        if self.parameters:
            value += ', ' + ', '.join([field + '=' + repr(value)
                                       for field, value in self.parameters.items()])
        return value + ')>'

    def _validate(self) -> None:
        """Validate provided arguments."""
        if self.backend == 'sqlite':
            self._validate_for_sqlite()
        else:
            self._validate_database()
            self._validate_user_and_password()

    def _validate_user_and_password(self) -> None:
        if self.user is not None and self.password is None:
            raise AttributeError('Must provide \'password\' if \'user\' provided')
        if self.user is None and self.password is not None:
            raise AttributeError('Must provide \'user\' if \'password\' provided')

    def _validate_for_sqlite(self) -> None:
        if self.file is None:
            raise AttributeError('Must provide \'file\' for SQLite')
        if self.database is not None:
            raise AttributeError('Must provide \'file\' not \'database\' for SQLite')
        for field in ('user', 'password', 'host', 'port'):
            if self.get(field) is not None:
                raise AttributeError(f'Cannot provide \'{field}\' for SQLite')

    def _validate_database(self) -> None:
        if self.file:
            raise AttributeError('Cannot provide \'file\' if not SQLite')
        if not self.database:
            raise AttributeError('Must provide \'database\' if not SQLite')

    def encode(self) -> str:
        """Construct URL string with encoded parameters."""
        return ''.join([
            f'{self.backend}://',
            self._format_user_and_password(),
            self._format_host_and_port(),
            self._format_database_or_file(),
            self._format_parameters(),
        ])

    def _format_parameters(self) -> str:
        if self.parameters:
            return '?' + urlencode(self.parameters)
        else:
            return ''

    def _format_database_or_file(self) -> str:
        if self.database:
            return f'/{self.database}'
        else:
            return f'/{self.file}'

    def _format_host_and_port(self) -> str:
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

    def _format_user_and_password(self) -> str:
        if self.user and self.password:
            return f'{self.user}:{self.password}@'
        else:
            return ''

    def __str__(self) -> str:
        return self.encode()

    @staticmethod
    def _strip_endings(value: str, *endings: str):
        """Removing instances of each possible `endings` from `value`."""
        r = str(value)
        for ending in endings:
            pos = len(ending)
            if r[-pos:] == ending:
                r = r[:-pos]
        return r

    @classmethod
    def from_namespace(cls, ns: Namespace) -> DatabaseURL:
        fields = {}
        for key in ns.keys():
            key_ = cls._strip_endings(key, '_env', '_eval')
            fields[key_] = getattr(ns, key_)
        return cls(**fields)


# allowed database backends
# mapping translates from name to library/package name (actual)
backends = {
    'sqlite': 'sqlite',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
}


config = Namespace(config.database.copy())
schema = config.pop('schema', None)
echo   = config.pop('echo', False)
connect_args = config.pop('connect_args', {})

if not isinstance(echo, bool):
    raise ConfigurationError('\'database.echo\' must be true or false')

try:
    params = Namespace(**{**config.copy(), **{'backend': backends[config.backend]}})
    url = DatabaseURL.from_namespace(params)
except AttributeError as error:
    raise ConfigurationError(str(error)) from error


if config.backend not in backends:
    raise ConfigurationError(f'Unsupported database \'{config.provider}\'')


try:
    engine = create_engine(url.encode(), connect_args=connect_args)
    engine.echo = echo
except ArgumentError as error:
    raise ConfigurationError(f'Database URL: {repr(url)}') from error


# create thread-local sessions
factory = sessionmaker(bind=engine)
Session = scoped_session(factory)
