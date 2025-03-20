# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Send notifications."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from refitt.admin.notify import mail
from refitt.admin.notify import slack

# public interface
__all__ = ['NotifyApp', ]


PROGRAM = f'refitt notify'
USAGE = f"""\
Usage: 
  {PROGRAM} [-h] <command> [<args>...]
  
  {__doc__}\
"""

HELP = f"""\
{USAGE}

Commands:
  mail               {mail.__doc__}
  slack              {slack.__doc__}

Options:
  -h, --help         Show this message and exit.\
"""


class NotifyApp(ApplicationGroup):
    """Application class for database command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'mail': mail.MailApp,
                'slack': slack.SlackApp,
                }
