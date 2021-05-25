# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Manage database."""


# external libs
from cmdkit.app import ApplicationGroup
from cmdkit.cli import Interface

# internal libs
from . import init, check, query

# public interface
__all__ = ['DatabaseApp', ]


PROGRAM = 'refitt database'
USAGE = f"""\
usage: {PROGRAM} [-h] <command> [<args>...]
{__doc__}\
"""

HELP = f"""\
{USAGE}

commands:
init                     {init.__doc__}
check                    {check.__doc__}
query                    {query.__doc__}

options:
-h, --help               Show this message and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.\
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
