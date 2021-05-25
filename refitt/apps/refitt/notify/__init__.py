# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Send notifications."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from . import mail, slack

# public interface
__all__ = ['NotifyApp', ]


PROGRAM = f'refitt notify'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
mail                     {mail.__doc__}
slack                    {slack.__doc__}

options:
-h, --help               Show this message and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.\
"""

class NotifyApp(ApplicationGroup):
    """Application class for database command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'mail': mail.MailApp,
                'slack': slack.SlackApp,
                }
