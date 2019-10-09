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

"""Defines default configuration and reads from /etc/refitt.yml."""

# standard libs
import os
import socket

# external libs
from cmdkit.config import Namespace, Configuration


# home directory
HOME = os.getenv('HOME')
if HOME is None:
    raise ValueError('"HOME" environment variable not defined.')

# retain for use elsewhere in refitt
HOSTNAME = socket.gethostname()

# environment variables
# ---------------------
# Load any environment variable that begins with "REFITT_".
# TODO: define variables for runtime configurability.
ENV_DEFAULTS = {'REFITT_SITE': os.getcwd()}
ENV = Namespace.from_env(prefix='REFITT_', defaults=ENV_DEFAULTS)


# runtime/configuration paths
# ---------------------------
SITE = {
    'system': {
        'lib': '/var/lib/refitt',
        'log': '/var/log/refitt',
        'run': '/var/run/refitt',
        'cfg': '/etc/refitt.yml'},
    'user': {
        'lib': f'{HOME}/.refitt/lib',
        'log': f'{HOME}/.refitt/log',
        'run': f'{HOME}/.refitt/run',
        'cfg': f'{HOME}/.refitt/config.yml'},
    'site': {
        'lib': f'{ENV["REFITT_SITE"]}/lib',
        'log': f'{ENV["REFITT_SITE"]}/log',
        'run': f'{ENV["REFITT_SITE"]}/run',
        'cfg': f'{ENV["REFITT_SITE"]}/etc/refitt.yml'},
}

# configuration files
# -------------------
# Load the system, user, and site level configuration files as `Namespace`s
# if and only if that file path exists, otherwise making it empty.
namespaces = dict()
for site, paths in SITE.items():
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
