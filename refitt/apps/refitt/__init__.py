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

"""The main console application, `refitt`."""

# standard libs
import sys

# internal libs
from ...core.logging import logger
from ...__meta__ import (__appname__, __version__, __description__,
                         __copyright__, __developer__, __contact__,
                         __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError

# subcommands
from .app_pipeline import PipelineApp
from .service_stream import StreamApp
from .service_webapi import WebAPIApp

SUB_COMMANDS = {
    'app.pipeline': PipelineApp,
    'service.stream': StreamApp,
    'service.webapi': WebAPIApp,
}

PROGRAM = __appname__

USAGE = f"""\
usage: {__appname__} [<group>[.<command>]] [<args>]
       {__appname__} [--help] [--version]

{__description__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

APP_GROUP = f"""\
    app
        .forecast      Build forecast for single candidate.
        .recommend     Build recommendations from forecasts.
        .pipeline      {PipelineApp.__doc__}
"""

SERVICE_GROUP = f"""\
    service
        .message       Message broker streaming service.
        .cluster       HPC job scheduling.
        .webapi        {WebAPIApp.__doc__}
        .stream        {StreamApp.__doc__}
"""

JOB_GROUP = f"""\
    job
        .submit        Submit jobs to the cluster.
        .delete        Delete jobs from the cluster.
        .status        Check the status of existing jobs.
"""

DATABASE_GROUP = f"""\
    database
        .select        Query database.
        .insert        Load records into database.
"""

TOOL_GROUP = f"""\
    tool
        .monitor       Monitor system resources.
        .sendmail      Send emails.
"""

LOG_GROUP = f"""\
    log
        .show          Show current log files.
        .gather        Collect all data.
        .process       Extract information from logs.
"""

HELP = f"""\
{USAGE}

commands:

{APP_GROUP}
{SERVICE_GROUP}
{JOB_GROUP}
{DATABASE_GROUP}
{LOG_GROUP}
{TOOL_GROUP}

options:

-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.

{EPILOG}
"""


HELP_GROUPS = {
    'app':      APP_GROUP,
    'service':  SERVICE_GROUP,
    'database': DATABASE_GROUP,
    'job':      JOB_GROUP,
    'log':      LOG_GROUP,
    'tool':     TOOL_GROUP,
}

# initialize module level logger
log = logger.with_name(__appname__)


class RefittMain(Application):
    """Application class for primary Refitt console-app."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('--version', version=__version__, action='version')

    subcommand: str = None
    interface.add_argument('subcommand')

    def run(self) -> None:
        """Show usage/help/version or defer to subcommand."""
        try:
            SUB_COMMANDS[self.subcommand].main(sys.argv[2:])
        except KeyError as error:
            cmd, = error.args
            if cmd in HELP_GROUPS:
                raise ArgumentError(f'"{cmd}" is a subcommand group. Use the --help flag to '
                                    f'see available subcommands.')
            else:
                raise ArgumentError(f'"{cmd}" is not an available subcommand.')


def main() -> int:
    """Entry-point for `refitt` console application."""
    return RefittMain.main(sys.argv[1:2])  # only first argument if present
