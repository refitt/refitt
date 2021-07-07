# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database config, engine, and session interface."""


# type annotations
from __future__ import annotations

# standard libs
from contextlib import contextmanager

# external libs
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError, ArgumentError
from sqlalchemy.orm import sessionmaker, scoped_session

# internal libs
from ..core.config import config, Namespace, ConfigurationError
from .url import DatabaseURL

# public interface
__all__ = ['providers', 'engine', 'schema', 'Session', 'config', ]


# allowed database providers
# mapping translates from name to library/package name (SQLAlchemy)
providers = {
    'sqlite': 'sqlite',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
    'timescale': 'postgresql',
    'timescaledb': 'postgresql',
}


config = Namespace(config.database)
schema = config.pop('schema', None)
echo = config.pop('echo', False)
connect_args = config.pop('connect_args', {})


if not isinstance(echo, bool):
    raise ConfigurationError('\'database.echo\' must be true or false')


if config.provider not in providers:
    raise ConfigurationError(f'Unsupported database provider \'{config.provider}\'')


def get_url() -> DatabaseURL:
    """Prepare DatabaseURL from configuration."""
    try:
        params = Namespace(config)
        params.provider = providers[config.provider]
        return DatabaseURL.from_namespace(params)
    except AttributeError as error:
        raise ConfigurationError(str(error)) from error


def get_engine() -> Engine:
    """Create engine instance from DatabaseURL."""
    url = get_url()
    try:
        __engine = create_engine(url.encode(), connect_args=connect_args)
        __engine.echo = echo
        return __engine
    except ArgumentError as error:
        raise ConfigurationError(f'Bad connection ({repr(url)})') from error


# create thread-local sessions
engine = get_engine()
factory = sessionmaker(bind=engine)
Session = scoped_session(factory)


@contextmanager
def transaction() -> Session:
    """Context manager for automatically rolling back a session upon errors."""
    try:
        yield Session
        Session.commit()
    except IntegrityError:
        Session.rollback()
        raise
