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
from ...core.apps import Application
from ...core.parser import ArgumentParser, ParserError
from ...core.logging import get_logger
from ...__meta__ import (__appname__, __version__, __description__,
                         __copyright__, __developer__, __contact__,
                         __website__)

# subcommands
from .app_pipeline import PipelineApp

SUB_COMMANDS = {'app.pipeline': PipelineApp,
                }

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
        .start         Start a service.
        .stop          Stop a running service.
        .restart       Restart a running service.
        .status        Check the status of a service.
"""

JOB_GROUP = f"""\
    job
        .submit        Submit jobs to the cluster.
        .delete        Delete jobs from the cluster.
        .status        Check the status of existing jobs.
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
{LOG_GROUP}

options:

-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.

{EPILOG}
"""

HELP_GROUPS = {'app': APP_GROUP,
               'service': SERVICE_GROUP,
               'job': JOB_GROUP,
               'log': LOG_GROUP}

# initialize module level logger
log = get_logger(__appname__)


class RefittMain(Application):
    """Application class for primary Refitt console-app."""

    interface = ArgumentParser(__appname__, USAGE, HELP)

    command: str = None
    interface.add_argument('command')
    interface.add_argument('--version', version=__version__, action='version')

    def run(self) -> None:
        """Show usage/help/version or defer to subcommand."""
        try:
            SUB_COMMANDS[self.command].main(sys.argv[2:])
        except KeyError as error:
            cmd, = error.args
            if cmd in HELP_GROUPS:
                raise ParserError(f'"{cmd}" is a command group. Use the --help flag to '
                                  f'see available subcommands.')
            else:
                raise ParserError(f'"{cmd}" is not an available command.')


def main() -> int:
    """Entry-point for `refitt` console application."""
    return RefittMain.main(sys.argv[1:2])  # only first argument if present
