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

"""Create and manage forecasts."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from . import create, publish


PROGRAM = 'refitt forecast'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
create                   {create.__doc__}
publish                  {publish.__doc__}

options:
-h, --help               Show this message and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.\
"""


class ForecastApp(ApplicationGroup):
    """Application class for forecast command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {
        'create': create.ForecastCreateApp,
        'publish': publish.ForecastPublishApp,
    }
