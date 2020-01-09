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
from typing import Dict

# standard libs
import os
import functools

# external libs
from cmdkit.config import Namespace, Configuration

# internal libs
from .logging import Logger
from ..__meta__ import __appname__

# module level logger
log = Logger.with_name(f'{__appname__}.config')


# home directory
HOME = os.getenv('HOME')
if HOME is None:
    raise ValueError('"HOME" environment variable not defined.')


# environment variables
# ---------------------
# Load any environment variable that begins with "{PREFIX}_".
# TODO: specify environment variables for runtime configurability.
PREFIX = __appname__.upper()
ENV_DEFAULTS = {f'{PREFIX}_SITE': os.getcwd()}
ENV = Namespace.from_env(prefix=f'{PREFIX}_', defaults=ENV_DEFAULTS)

# runtime/configuration paths
# ---------------------------
ROOT = True if os.getuid() == 0 else False
SITE = 'system' if ROOT else 'user'
SITE = SITE if f'{PREFIX}_SITE' not in os.environ else ENV[f'{PREFIX}_SITE']
LOCAL_SITE = ENV[f'{PREFIX}_SITE']
SITEMAP = {
    'system': {
        'lib': f'/var/lib/{__appname__}',
        'log': f'/var/log/{__appname__}',
        'run': f'/var/run/{__appname__}',
        'cfg': f'/etc/{__appname__}.yml'},
    'user': {
        'lib': f'{HOME}/.{__appname__}/lib',
        'log': f'{HOME}/.{__appname__}/log',
        'run': f'{HOME}/.{__appname__}/run',
        'cfg': f'{HOME}/.{__appname__}/config.yml'},
    'site': {
        'lib': f'{LOCAL_SITE}/.{__appname__}/lib',
        'log': f'{LOCAL_SITE}/.{__appname__}/log',
        'run': f'{LOCAL_SITE}/.{__appname__}/run',
        'cfg': f'{LOCAL_SITE}/.{__appname__}/config.yml'},
}


@functools.lru_cache(maxsize=1)
def get_site() -> Dict[str, str]:
    """
    Return the runtime site.
    Automatically creates directories if needed.
    """
    site = SITEMAP[SITE]
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
    config = Configuration(**namespaces)
    return config


# global instance
# some uses may reload this
config = get_config()


class ConfigurationError(Exception):
    """Exception specif to configuration errors."""
