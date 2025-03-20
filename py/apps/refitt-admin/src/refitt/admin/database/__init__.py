# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Manage database."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from refitt.admin.database import check, query
from refitt.admin.database import init

# public interface
__all__ = ['DatabaseApp', ]


PROGRAM = 'refitt database'
USAGE = f"""\
Usage: 
  {PROGRAM} [-h] <command> [<args>...]
  
  {__doc__}\
"""

HELP = f"""\
{USAGE}

Commands:
  init              {init.__doc__}
  check             {check.__doc__}
  query             {query.__doc__}

Options:
  -h, --help        Show this message and exit.\
"""


class DatabaseApp(ApplicationGroup):
    """Application class for database command group."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')

    command = None
    commands = {'init': init.InitDatabaseApp,
                'check': check.CheckDatabaseApp,
                'query': query.QueryDatabaseApp,
                }
