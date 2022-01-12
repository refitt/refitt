# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""
Runtime configuration for REFITT.

Files:
         /etc/refitt.toml    System
    ~/.refitt/config.toml    User
      .refitt/config.toml    Local
"""


# standard libs
import os
import functools
import logging

# external libs
from cmdkit.config import Namespace, Configuration, ConfigurationError  # noqa: unused
from streamkit.core import config as _streamkit

# public interface
__all__ = ['config', 'get_config', 'get_site', 'update_config', 'SITE', 'PATH', 'DEFAULT',
           'ConfigurationError', 'Namespace', ]


# module level logger
log = logging.getLogger(__name__)


CWD = os.getcwd()
HOME = os.getenv('HOME')
ROOT = os.getuid() == 0
SITE = 'system' if ROOT else 'user'
PATH = Namespace({
    'system': {
        'lib': '/var/lib/refitt',
        'log': '/var/log/refitt',
        'run': '/var/run/refitt',
        'config': '/etc/refitt.toml'},
    'user': {
        'lib': f'{HOME}/.refitt/lib',
        'log': f'{HOME}/.refitt/log',
        'run': f'{HOME}/.refitt/run',
        'config': f'{HOME}/.refitt/config.toml'},
    'local': {
        'lib': f'{CWD}/.refitt/lib',
        'log': f'{CWD}/.refitt/log',
        'run': f'{CWD}/.refitt/run',
        'config': f'{CWD}/.refitt/config.toml'},
})


# environment variables and configuration files are automatically
# depth-first merged with defaults
DEFAULT = Namespace({

    'database': {
            'provider': 'sqlite',
    },

    'logging': {
        'level': 'warning',
        'format': '%(asctime)s %(hostname)s %(levelname)-8s [%(name)s] %(msg)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'stream': {
            'enabled': False,
            'batchsize': 10,
            'timeout': 5
        }
    },

    'api': {
        'site': 'https://api.refitt.org',
        'port': None,
        'login': 'https://refitt.org/api_credentials'
    },

    'daemon': {
        'port': 50000,
        'key': '__REFITT__DAEMON__KEY__',  # this should be overridden
        'refresh': 10,  # seconds to wait before issuing keep-alive to services
        'timeout': 4,   # seconds to wait before hard kill services on interrupt
    },

    'plasma': {
        'memory': 1_000_000,  # 1 MB
        'socket': ''
    }
})


@functools.lru_cache(maxsize=None)
def get_site(key: str = None) -> Namespace:
    """
    Return the file-system structure based on `key`.
    Automatically creates directories if needed.
    """
    site = PATH[SITE] if key is None else PATH[key]
    for folder in ['lib', 'log', 'run']:
        if not os.path.isdir(site[folder]):
            log.debug(f'creating directory {site[folder]}')
            os.makedirs(site[folder], exist_ok=True)
    return site


def get_config() -> Configuration:
    """Load configuration."""
    return Configuration.from_local(env=True,
                                    prefix='REFITT',
                                    default=DEFAULT,
                                    system=PATH.system.config,
                                    user=PATH.user.config,
                                    local=PATH.local.config)


# single global instance
config = get_config()


def update_config(site: str, data: dict) -> None:
    """
    Extend the current configuration and commit it to disk.

    Args:
        site (str):
            Either "local", "user", or "system"
        data (dict):
            Sectioned mappable to update configuration file.

    Example:
        >>> update_config('user', {
        ...    'database': {
        ...        'user': 'ABC123'
        ...    }
        ... })
    """
    path = get_site(site).config
    new_config = Namespace.from_local(path, ignore_if_missing=True)
    new_config.update(data)
    new_config.to_local(path)


# inject configuration back into streamkit library
# this needs to happen before streamkit is imported anywhere
db_conf = Namespace(config.database)
db_conf['backend'] = db_conf.pop('provider')
_streamkit.config.extend(refitt=Namespace({
   'database': db_conf,
   'logging': config.logging
}))
