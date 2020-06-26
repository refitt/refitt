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

"""Runtime configuration for REFITT."""

# type annotations
from typing import Dict, Mapping

# standard libs
import os
import functools
import subprocess

# external libs
from cmdkit.config import Namespace, Configuration
import toml

# internal libs
from .logging import Logger
from ..assets import load_asset
from ..__meta__ import __appname__

# module level logger
log = Logger(__name__)


# home directory
HOME = os.getenv('HOME', None)
if HOME is None:
    raise ValueError('"HOME" environment variable not defined.')

# global variables
VARS = {
    'SITE': os.getcwd(),
    'DAEMON_PORT': '50000',
    'DAEMON_KEY':  '__REFITT__DAEMON__KEY__',
    'DAEMON_REFRESH_TIME': '10',   # seconds
    'DAEMON_INTERRUPT_TIMEOUT': '4',  # seconds
    'DATABASE_PROFILE': 'default',
    'DATABASE': 'refitt',
    'PLASMA_MEMORY': 1_000_000,
    'PLASMA_SOCKET': '/tmp/plasma.sock',
}

# environment variables
# ---------------------
# Load any environment variable that begins with "{PREFIX}_".
PREFIX = __appname__.upper()
ENV_DEFAULTS = {f'{PREFIX}_{name}': value for name, value in VARS.items()}
ENV = Namespace.from_env(prefix=f'{PREFIX}_', defaults=ENV_DEFAULTS)

# update VARS to include ENV overrides
for name, value in ENV.items():
    VARS[name[len(PREFIX)+1:]] = value

# runtime/configuration paths
# ---------------------------
ROOT = os.getuid() == 0
SITE = 'system' if ROOT else 'user'
SITE = SITE if f'{PREFIX}_SITE' not in os.environ else 'site'
LOCAL_SITE = ENV[f'{PREFIX}_SITE']
SITEMAP = {
    'system': {
        'lib': f'/var/lib/{__appname__}',
        'log': f'/var/log/{__appname__}',
        'run': f'/var/run/{__appname__}',
        'cfg': f'/etc/{__appname__}.toml'},
    'user': {
        'lib': f'{HOME}/.{__appname__}/lib',
        'log': f'{HOME}/.{__appname__}/log',
        'run': f'{HOME}/.{__appname__}/run',
        'cfg': f'{HOME}/.{__appname__}/config.toml'},
    'site': {
        'lib': f'{LOCAL_SITE}/.{__appname__}/lib',
        'log': f'{LOCAL_SITE}/.{__appname__}/log',
        'run': f'{LOCAL_SITE}/.{__appname__}/run',
        'cfg': f'{LOCAL_SITE}/.{__appname__}/config.toml'},
}


@functools.lru_cache(maxsize=1)
def get_site(key: str = None) -> Dict[str, str]:
    """
    Return the runtime site.
    Automatically creates directories if needed.
    """
    site = SITEMAP[SITE] if key is None else SITEMAP[key]
    for folder in ['lib', 'log', 'run']:
        if not os.path.isdir(site[folder]):
            log.info(f'creating directory {site[folder]}')
            os.makedirs(site[folder])
    return site


def get_config() -> Configuration:
    """Load configuration."""
    # configuration files
    # -------------------
    # Load the system, user, and site level configuration files as `Namespace`s
    # if and only if that file path exists, otherwise making it empty.
    namespaces = dict()
    for site, paths in SITEMAP.items():
        filepath = paths['cfg']
        if os.path.exists(filepath):
            namespaces[site] = Namespace.from_local(filepath)
        else:
            namespaces[site] = Namespace()

    # runtime configuration
    # ---------------------
    # Merge each available namespace into a single `ChainMap` like structure.
    # A call to __getitem__ returns in a reverse-order depth-first search.
    return Configuration(**namespaces)


def init_config(key: str = None) -> None:
    """Initialize configuration with defaults if necessary."""
    site = SITE if key is None else key
    path = SITEMAP[site]['cfg']
    if not os.path.exists(path):
        default = toml.loads(load_asset('config/refitt.toml'))
        with open(path, mode='w') as config_file:
            toml.dump(default, config_file)


# global instance
# some uses may reload this
config = get_config()


class ConfigurationError(Exception):
    """Exception specif to configuration errors."""


def expand_parameters(prefix: str, namespace: Namespace) -> str:
    """Substitute values into namespace if `_env` or `_eval` present."""
    value = None
    count = 0
    for key in filter(lambda _key: _key.startswith(prefix), namespace.keys()):
        count += 1
        if count > 1:
            raise ValueError(f'more than one variant of "{prefix}" in configuration file')
        if key.endswith('_env'):
            value = os.getenv(namespace[key])
            log.debug(f'expanded "{prefix}" from configuration as environment variable')
        elif key.endswith('_eval'):
            value = subprocess.check_output(namespace[key].split()).decode().strip()
            log.debug(f'expanded "{prefix}" from configuration as shell command')
        elif key == prefix:
            value = namespace[key]
        else:
            raise ValueError(f'unrecognized variant of "{prefix}" ({key}) in configuration file')
    return value


def update_config(site: str, data: Mapping) -> None:
    """
    Extend the current configuration and commit it to disk.

    Example
    -------
    >>> from refitt.core.config import update_config
    >>> update_config('user', {
        'api': {
            'access_token': 'ABC123'
        }
    })
    """
    get_site(site)  # ensure directories
    init_config(site)  # ensure default exists
    new_config = Configuration(old=get_config().namespaces[site],
                               new=Namespace(data))
    # commit to file
    new_config._master.to_local(SITEMAP[site]['cfg'])
