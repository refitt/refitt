# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""Manage configuration."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from . import get, set, edit, which


PROGRAM = 'refitt config'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
get                      {get.__doc__}
set                      {set.__doc__}
edit                     {edit.__doc__}
which                    {which.__doc__}

options:
-h, --help               Show this message and exit.

files:
/etc/refitt.toml         System configuration.
~/.refitt/config.toml    User configuration.
./.refitt/config.toml    Local configuration.

Use the -h/--help flag with the above commands to
learn more about their usage.\
"""


class ConfigApp(ApplicationGroup):
    """Application class for config command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'get': get.GetConfigApp,
                'set': set.SetConfigApp,
                'edit': edit.EditConfigApp,
                'which': which.WhichConfigApp, }
