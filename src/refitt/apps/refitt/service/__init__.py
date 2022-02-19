# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Run services."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from . import api, stream, test, tns


PROGRAM = 'refitt service'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
api                 {api.__doc__}
tns                 {tns.__doc__}
stream              {stream.__doc__}

options:
-h, --help          Show this message and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.\
"""

class ServiceApp(ApplicationGroup):
    """Application class for service command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'api': api.WebApp,
                'stream': stream.StreamApp,
                'tns': tns.TNSApp,
                'test': test.TestApp, }
