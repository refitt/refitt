# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Runtime configuration."""


# type annotations
from __future__ import annotations
from typing import Optional, Protocol

# standard libs
import os
import sys
import functools

# external libs
from cmdkit.app import exit_status
from cmdkit.config import Namespace, Environ, Configuration, ConfigurationError
from streamkit.core import config as _streamkit

# internal libs
from refitt.core.platform import path, default_path, check_private
from refitt.core.exceptions import write_traceback, display_warning

# public interface
__all__ = ['config', 'update', 'default', 'ConfigurationError', 'Namespace', 'blame',
           'load', 'reload', 'load_file', 'reload_file', 'load_env', 'reload_env',
           'DEFAULT_LOGGING_STYLE', 'DEFAULT_DATABASE', 'LOGGING_STYLES', ]


DEFAULT_LOGGING_STYLE = 'default'
LOGGING_STYLES = {
    'default': {
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'format': ('%(ansi_bold)s%(ansi_level)s%(levelname)8s%(ansi_reset)s %(ansi_faint)s[%(name)s]%(ansi_reset)s'
                   ' %(message)s'),
    },
    'system': {
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'format': '%(asctime)s.%(msecs)03d %(hostname)s %(levelname)8s [%(app_id)s] [%(name)s] %(message)s',
    },
    'detailed': {
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'format': ('%(ansi_faint)s%(asctime)s.%(msecs)03d %(hostname)s %(ansi_reset)s'
                   '%(ansi_level)s%(ansi_bold)s%(levelname)8s%(ansi_reset)s '
                   '%(ansi_faint)s[%(name)s]%(ansi_reset)s %(message)s'),
    }
}


# Default SQLite database location if not configured
DEFAULT_DATABASE = os.path.join(default_path.lib, 'main.db')


# environment variables and configuration files are automatically
# depth-first merged with defaults
default = Namespace({

    'database': {
            # NOTE: If not configured the default is ~/.refitt/lib/main.db
            # See `auto_database` below
            'provider': 'sqlite',
    },

    'logging': {
        'level': 'warning',
        'stream': {
            'enabled': False,
            'batchsize': 10,
            'timeout': 5
        },
        # NOTE: If a 'style' is defined than other parameters can be overridden
        'style': DEFAULT_LOGGING_STYLE,
        **LOGGING_STYLES.get(DEFAULT_LOGGING_STYLE),
    },

    'api': {
        'site': 'https://api.refitt.org',
        'port': None,
        'login': 'https://refitt.org/api_credentials'
    },

    'daemon': {
        'port': 50000,
        'key': '__REFITT__DAEMON__KEY__',  # Should be overridden
        'refresh': 10,  # Seconds to wait before issuing keep-alive to services
        'timeout': 4,   # Seconds to wait before hard kill services on failed interrupt
    },

    'plasma': {
        'memory': 1_000_000,  # 1 MB
        'socket': ''
    },

    'console': {
        'theme': 'solarized-dark',
    },
})


def reload_file(filepath: str) -> Namespace:
    """Force reloading configuration file."""
    if not os.path.exists(filepath):
        return Namespace({})
    if not check_private(filepath):
        raise ConfigurationError(f'Non-private file permissions ({filepath})')
    try:
        return Namespace.from_toml(filepath)
    except Exception as err:
        raise ConfigurationError(f'(from file: {filepath}) {err.__class__.__name__}: {err}')


@functools.lru_cache(maxsize=None)
def load_file(filepath: str) -> Namespace:
    """Load configuration file."""
    return reload_file(filepath)


def reload_env() -> Environ:
    """Force reloading environment variables and expanding hierarchy as namespace."""
    return Environ(prefix='REFITT').expand()


@functools.lru_cache(maxsize=None)
def load_env() -> Environ:
    """Load environment variables and expand hierarchy as namespace."""
    return reload_env()


def partial_load(**preload: Namespace) -> Configuration:
    """Load configuration from files and merge environment variables."""
    return Configuration(**{
        'default': default, **preload,
        'system': load_file(path.system.config),
        'user': load_file(path.user.config),
        'local': load_file(path.local.config),
        'env': load_env(),
    })


def partial_reload(**preload: Namespace) -> Configuration:
    """Force reload configuration from files and merge environment variables."""
    return Configuration(**{
        'default': default, **preload,
        'system': reload_file(path.system.config),
        'user': reload_file(path.user.config),
        'local': reload_file(path.local.config),
        'env': reload_env(),
    })


def blame(base: Configuration, *varpath: str) -> Optional[str]:
    """Construct filename or variable assignment string based on precedent of `varpath`"""
    source = base.which(*varpath)
    if not source:
        return None
    if source in ('system', 'user', 'local'):
        return f'from: {path.get(source).config}'
    elif source == 'env':
        return 'from: REFITT_' + '_'.join([node.upper() for node in varpath])
    else:
        return f'from: <{source}>'


def get_logging_style(base: Configuration) -> str:
    """Get and check valid on `config.logging.style`."""
    style = base.logging.style
    label = blame(base, 'logging', 'style')
    if not isinstance(style, str):
        raise ConfigurationError(f'Expected string for `logging.style` ({label})')
    style = style.lower()
    if style in LOGGING_STYLES:
        return style
    else:
        raise ConfigurationError(f'Unrecognized `logging.style` \'{style}\' ({label})')


def build_preloads(base: Configuration) -> Namespace:
    """Build 'preload' namespace from base configuration."""
    ns = Namespace()
    ns.update({'logging': LOGGING_STYLES.get(get_logging_style(base))})
    if base.database == default.database:
        display_warning(f'Using default database ({DEFAULT_DATABASE})')
        ns.update({'database': {'file': DEFAULT_DATABASE}})
    return ns


class LoaderImpl(Protocol):
    """Loader interface for building configuration."""
    def __call__(self: LoaderImpl, **preloads: Namespace) -> Configuration: ...


def build_configuration(loader: LoaderImpl) -> Configuration:
    """Construct full configuration."""
    return loader(preload=build_preloads(base=loader()))


def load() -> Configuration:
    """Load configuration from files and merge environment variables."""
    return build_configuration(loader=partial_load)


def reload() -> Configuration:
    """Load configuration from files and merge environment variables."""
    return build_configuration(loader=partial_reload)


try:
    config = load()
except Exception as error:
    write_traceback(error, module=__name__)
    sys.exit(exit_status.bad_config)


def update(scope: str, data: dict) -> None:
    """Extend the current configuration and commit it to disk."""
    config_path = path[scope].config
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    new_config = Namespace.from_local(config_path)
    new_config.update(data)
    new_config.to_local(config_path)


# Inject configuration back into streamkit library
db_conf = Namespace(config.database)
db_conf['backend'] = db_conf.pop('provider')  # FIXME: StreamKit inconsistency
_streamkit.config.extend(refitt=Namespace({
   'database': db_conf,
   'logging': config.logging
}))
