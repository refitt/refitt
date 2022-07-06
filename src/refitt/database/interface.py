# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database config, engine, and session interface."""


# type annotations
from __future__ import annotations

# standard libs
import sys
from contextlib import contextmanager

# external libs
from cmdkit.app import exit_status
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError, ArgumentError
from sqlalchemy.orm import sessionmaker, scoped_session

# internal libs
from refitt.core.exceptions import write_traceback
from refitt.core.logging import Logger, handler, INFO
from refitt.core.config import config, Namespace, ConfigurationError
from refitt.database.url import DatabaseURL

# public interface
__all__ = ['providers', 'engine', 'schema', 'Session', 'config', ]


# Allowed database providers
# Mapping translates from name to library/package name (SQLAlchemy)
providers = {
    'sqlite': 'sqlite',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
    'timescale': 'postgresql',
    'timescaledb': 'postgresql',
}


config = Namespace(config.database)
schema = config.pop('schema', None)
engine_echo = config.pop('echo', False)
connect_args = config.pop('connect_args', {})


def get_url() -> DatabaseURL:
    """Prepare DatabaseURL from configuration."""
    if config.provider not in providers:
        raise ConfigurationError(f'Unsupported database provider \'{config.provider}\'')
    try:
        params = Namespace(config)
        params.provider = providers[config.provider]
        return DatabaseURL.from_namespace(params)
    except AttributeError as error:
        raise ConfigurationError(str(error)) from error


def get_engine() -> Engine:
    """Create engine instance from DatabaseURL."""
    if not isinstance(engine_echo, bool):
        raise ConfigurationError('\'database.echo\' must be true or false')
    try:
        if engine_echo:
            log = Logger.with_name('sqlalchemy.engine')
            log.addHandler(handler)
            log.setLevel(INFO)
        return create_engine(get_url().encode(), connect_args=connect_args)
    except ArgumentError as error:
        raise ConfigurationError(f'Database engine: ({error})') from error


try:
    engine = get_engine()
    factory = sessionmaker(bind=engine)
    Session = scoped_session(factory)
except Exception as exc:
    write_traceback(exc, module=__name__)
    sys.exit(exit_status.bad_config)


@contextmanager
def transaction() -> Session:
    """Context manager for automatically rolling back a session upon errors."""
    try:
        yield Session
        Session.commit()
    except IntegrityError:
        Session.rollback()
        raise
