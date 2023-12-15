# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database config, engine, and session interface."""


# type annotations
from __future__ import annotations
from typing import Dict, Type

# standard libs
import os
import sys
from functools import cache, cached_property

# external libs
from cmdkit.app import exit_status
from cmdkit.config import Namespace, Configuration, ConfigurationError
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker, scoped_session

# internal libs
from refitt.core.platform import default_path
from refitt.core.exceptions import write_traceback
from refitt.core.logging import Logger, handler, INFO
from refitt.core.config import config, DEFAULT_DATABASE_NAME
from refitt.database.core import DatabaseConfiguration

# public interface
__all__ = ['provider_name_translation', 'ConnectionManager', 'default_connection', ]

# module logger
log = Logger.with_name(__name__)


# Allowed database providers
# Mapping translates from name to library/package name (SQLAlchemy)
provider_name_translation = {
    'sqlite': 'sqlite',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
    'timescale': 'postgresql',
    'timescaledb': 'postgresql',
}


class ConnectionManager:
    """Session manager for read/write connections to local and remote databases."""

    _full_config: Configuration
    _config: Dict[str, DatabaseConfiguration]
    _engine: Dict[str, Engine]
    _factory: Dict[str, sessionmaker]
    _session: Dict[str, scoped_session]

    def __init__(self: ConnectionManager, _config: Configuration) -> None:
        """Initialization does not establish sessions."""
        self._full_config = _config
        self._config = {}
        self._engine = {}
        self._factory = {}
        self._session = {}

    @classmethod
    def default(cls: Type[ConnectionManager]) -> ConnectionManager:
        """Access global default manager."""
        return default_connection

    @cache
    def local(self: ConnectionManager, name: str = DEFAULT_DATABASE_NAME) -> scoped_session:
        """Return database session for local SQLite database."""
        return ConnectionManager(get_local(name)).write

    @cached_property
    def read(self: ConnectionManager) -> scoped_session:
        """Return session scoped for read access to production database."""
        return self.get_session(self.name_from_scope('read'))

    @cached_property
    def write(self: ConnectionManager) -> scoped_session:
        """Return session scoped for write access to production database."""
        return self.get_session(self.name_from_scope('write'))

    @cache
    def name_from_scope(self: ConnectionManager, scope: str) -> str:
        """Parse name from scope in configuration."""
        return self._full_config.database.scope.get(scope)

    @cache
    def get_session(self: ConnectionManager, name: str) -> scoped_session:
        """Return scoped session for database."""
        try:
            self._config[name] = self.get_config(name)
            self._engine[name] = self.get_engine(name)
            self._factory[name] = sessionmaker(bind=self._engine[name])
            self._session[name] = scoped_session(self._factory[name])
            return self._session[name]
        except Exception as error:
            raise ConfigurationError(str(error)) from error

    @cache
    def get_engine(self: ConnectionManager, name: str) -> Engine:
        """Create engine instance for the given scope."""
        scoped_config = self.get_config(name)
        if not isinstance(scoped_config.echo, bool):
            raise ConfigurationError(f'\'database.{name}.echo\' must be true or false')
        if name == 'mem':
            return self.create_engine('sqlite://')
        try:
            if scoped_config.echo:
                sql_log = Logger.with_name('sqlalchemy.engine')
                sql_log.addHandler(handler)
                sql_log.setLevel(INFO)
            return self.create_engine(scoped_config.encode(), **scoped_config.connect_args)
        except ArgumentError as error:
            raise ConfigurationError(f'Database engine: ({error})') from error

    @cache
    def create_engine(self: ConnectionManager, uri: str, **connect_args) -> Engine:
        """Cache engine creation against URI."""
        return create_engine(uri, connect_args=connect_args)

    @cache
    def get_config(self: ConnectionManager, name: str) -> DatabaseConfiguration:
        """Prepare DatabaseConfiguration from configuration."""
        scoped_config = self.get_scope(name)
        if scoped_config.provider not in provider_name_translation:
            raise ConfigurationError(f'Unsupported database provider \'{scoped_config.provider}\'')
        try:
            scoped_config.update({'provider': provider_name_translation[scoped_config.provider]})
            return DatabaseConfiguration.from_namespace(scoped_config)
        except AttributeError as error:
            raise ConfigurationError(str(error)) from error

    @cache
    def get_scope(self: ConnectionManager, name: str) -> Configuration:
        """Build merged configuration for database scope."""
        if name == 'default':
            return self._full_config.database.default
        if name not in self._full_config.database:
            raise ConfigurationError(f'Missing section \'database.{name}\'')
        else:
            return Configuration(
                default=self._full_config.database.default,
                specific=self._full_config.database.get(name)
            )


def get_local(name: str = DEFAULT_DATABASE_NAME) -> Configuration:
    """Generate configuration for write-access to local SQLite database."""
    path = os.path.join(default_path.lib, f'{name}.db')
    cfg = {'database': {'default': {'provider': 'sqlite', 'file': path}, 'scope': {'write': 'default'}}}
    return Configuration(local=Namespace(cfg))


try:
    default_connection = ConnectionManager(config)
except Exception as exc:
    write_traceback(exc, module=__name__)
    sys.exit(exit_status.bad_config)
