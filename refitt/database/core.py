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


# initialize module level logger
log = logging.getLogger(__name__)


class URL(dict):
    """
    Dictionary-like structure for representing a connection string.

    Something like:
        backend://[[user[:password]@]host[:port]]/[database][?params...]
    """

    def __init__(self, backend: str, database: str, user: str = None, password: str = None,
                 host: str = None, port: int = None, **parameters) -> None:
        super().__init__(backend=backend, database=database, user=user, password=password,
                         host=host, port=port, parameters=parameters)

    def __repr__(self) -> str:
        masked = repr({key: value if key != 'password' else ('***' if self.password else None)
                       for key, value in self.items()})
        return f'<URL({masked})>'

    def __getattr__(self, item: str) -> Any:
        return self.get(item)

    def encode(self) -> str:
        """Construct URL string with encoded parameters."""

        url = f'{self.backend}://'

        if self.user and self.password:
            url += f'{self.user}:{self.password}@'
        elif self.user and not self.password:
            url += f'{self.user}@'
        elif self.password and not self.user:
            raise ConfigurationError('Missing \'password\' for \'user\'')

        if self.host and self.port:
            url += f'{self.host}:{self.port}'
        elif self.host and not self.port:
            url += f'{self.host}'
        elif self.port and not self.host:
            url += f'localhost:{self.port}'

        if self.database:
            url += f'/{self.database}'

        if self.parameters:
            encoded_params = urlencode(self.parameters)
            url += f'?{encoded_params}'

        return url

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
    def from_namespace(cls, ns: Namespace) -> URL:
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
    'timescaledb': 'postgresql',
}


config = config.database
schema = config.pop('schema', None)
connect_args = config.pop('connect_args', {})


if config.backend not in backends:
    raise ConfigurationError(f'Unsupported backend \'{config.backend}\'')


# NOTE: TimescaleDB is actually PostgreSQL
_url_params = Namespace(**{**config.copy(), **{'backend': backends[config.backend]}})
_url = URL.from_namespace(_url_params)
try:
    engine = create_engine(_url.encode(), connect_args=connect_args)
except ArgumentError as error:
    raise ConfigurationError(f'Backend config: {repr(_url)}') from error


# create thread-local sessions
factory = sessionmaker(bind=engine)
Session = scoped_session(factory)
