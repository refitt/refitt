# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Runtime files and folders."""


# standard libs
import os
import stat

# external libs
from cmdkit.config import Namespace

# public interface
__all__ = ['cwd', 'home', 'root', 'site', 'path', 'default_path', 'file_permissions', 'check_private']


cwd = os.getcwd()
home = os.getenv('HOME')
root = os.getuid() == 0
site = 'system' if root else 'user'
path = Namespace({
    'system': {
        'lib': '/var/lib/refitt',
        'log': '/var/log/refitt',
        'run': '/var/run/refitt',
        'config': '/etc/refitt.toml'},
    'user': {
        'lib': f'{home}/.refitt/lib',
        'log': f'{home}/.refitt/log',
        'run': f'{home}/.refitt/run',
        'config': f'{home}/.refitt/config.toml'},
    'local': {
        'lib': f'{cwd}/.refitt/lib',
        'log': f'{cwd}/.refitt/log',
        'run': f'{cwd}/.refitt/run',
        'config': f'{cwd}/.refitt/config.toml'},
})


# Automatically initialize default site directories
default_path = path.system if root else path.user
os.makedirs(default_path.lib, exist_ok=True)
os.makedirs(default_path.run, exist_ok=True)
os.makedirs(default_path.log, exist_ok=True)


def file_permissions(filepath: str) -> str:
    """File permissions mask as a string."""
    return stat.filemode(os.stat(filepath).st_mode)


def check_private(filepath: str) -> bool:
    """Check that `filepath` has '-rw-------' permissions."""
    return file_permissions(filepath) == '-rw-------'
