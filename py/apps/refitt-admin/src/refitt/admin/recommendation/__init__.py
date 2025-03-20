# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Create and manage recommendations."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from refitt.admin.recommendation import publish

# public interface
__all__ = ['RecommendationApp']


PROGRAM = 'refitt recommendation'
USAGE = f"""\
Usage: 
  {PROGRAM} [-h] <command> [<args>...]

  {__doc__}\
"""

HELP = f"""\
{USAGE}

Commands:
  publish             {publish.__doc__}

options:
  -h, --help          Show this message and exit.\
"""


class RecommendationApp(ApplicationGroup):
    """Application class for recommendation command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {
        'publish': publish.RecommendationPublishApp,
    }
