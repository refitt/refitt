# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Create and manage forecasts."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from refitt.admin.forecast import create, publish

# public interface
__all__ = ['ForecastApp', ]


PROGRAM = 'refitt forecast'
USAGE = f"""\
Usage: 
  {PROGRAM} [-h] <command> [<args>...]

  {__doc__}\
"""

HELP = f"""\
{USAGE}

Commands:
  create            {create.__doc__}
  publish           {publish.__doc__}

Options:
  -h, --help        Show this message and exit.\
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
