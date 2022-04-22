# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""
Runtime configuration for REFITT.

Files:
         /etc/refitt.toml    System
    ~/.refitt/config.toml    User
      .refitt/config.toml    Local
"""


# standard libs
import logging

# external libs
from cmdkit.config import Namespace, Configuration, ConfigurationError
from streamkit.core import config as _streamkit

# internal libs
from refitt.core.platform import path

# public interface
__all__ = ['config', 'get_config', 'update_config', 'DEFAULT',
           'ConfigurationError', 'Namespace', ]


# module level logger
log = logging.getLogger(__name__)


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


def get_config() -> Configuration:
    """Load configuration."""
    return Configuration.from_local(env=True,
                                    prefix='REFITT',
                                    default=DEFAULT,
                                    system=path.system.config,
                                    user=path.user.config,
                                    local=path.local.config)


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
    config_path = path.get(site).config
    new_config = Namespace.from_local(config_path, ignore_if_missing=True)
    new_config.update(data)
    new_config.to_local(config_path)


# inject configuration back into streamkit library
# this needs to happen before streamkit is imported anywhere
db_conf = Namespace(config.database)
db_conf['backend'] = db_conf.pop('provider')
_streamkit.config.extend(refitt=Namespace({
   'database': db_conf,
   'logging': config.logging
}))
