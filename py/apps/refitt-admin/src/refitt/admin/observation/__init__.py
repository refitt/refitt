# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Process and publish observation data."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from refitt.admin.observation import publish, reduce

# public interface
__all__ = ['ObservationApp']


PROGRAM = 'refitt observation'
USAGE = f"""\
Usage: 
  {PROGRAM} [-h] <command> [<args>...]
  
  {__doc__}\
"""

HELP = f"""\
{USAGE}

Commands:
  reduce             {reduce.__doc__}
  publish            {publish.__doc__}

Options:
  -h, --help         Show this message and exit.\
"""


class ObservationApp(ApplicationGroup):
    """Application class for observation command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {
        'reduce': reduce.ObservationReduceApp,
        'publish': publish.ObservationPublishApp,
    }
