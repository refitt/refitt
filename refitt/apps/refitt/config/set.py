# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Set variable in configuration file."""


# type annotations
from __future__ import annotations
from typing import TypeVar

# standard libs
import os
import logging

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# internal libs
from ....core.config import SITE, PATH, update_config

# public interface
__all__ = ['SetConfigApp', ]


PROGRAM = 'refitt config set'
USAGE = f"""\
usage: {PROGRAM} [-h] SECTION[...].VAR VALUE [--system | --user | --local]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
SECTION[...].VAR        Path to variable.
VALUE                   Value to be set.

options:
    --system            Apply to system configuration.
    --user              Apply to user configuration.
    --local             Apply to local configuration.
-h, --help              Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


SmartType = TypeVar('SmartType', int, float, str)
def smart_type(init_value: str) -> SmartType:
    """Passively coerce `init_value` to int or float if possible."""
    try:
        return int(init_value)
    except ValueError:
        try:
            return float(init_value)
        except ValueError:
            pass
    return init_value


class SetConfigApp(Application):
    """Application class for config set command."""

    interface = Interface(PROGRAM, USAGE, HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    value: str = None
    interface.add_argument('value', type=smart_type)

    local: bool = False
    user: bool = False
    system: bool = False
    site_interface = interface.add_mutually_exclusive_group()
    site_interface.add_argument('--local', action='store_true')
    site_interface.add_argument('--user', action='store_true')
    site_interface.add_argument('--system', action='store_true')

    def run(self) -> None:
        """Business logic for `config set`."""

        site = SITE
        path = PATH[site].config
        for key in ('local', 'user', 'system'):
            if getattr(self, key) is True:
                site = key
                path = PATH[site].config

        if not os.path.exists(path):
            raise RuntimeError(f'{path} does not exist')

        # parse variable specification
        if '.' not in self.varpath:
            raise ArgumentError('missing section in variable path')

        section, *subsections, variable = self.varpath.split('.')

        config = {section: {}}
        config_section = config[section]
        for subsection in subsections:
            if subsection not in config_section:
                config_section[subsection] = dict()
            config_section = config_section[subsection]

        config_section[variable] = self.value
        update_config(site, config)
