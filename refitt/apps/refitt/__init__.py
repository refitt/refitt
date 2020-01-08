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
from ...core.logging import Logger
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
from .data_select import DataSelectApp
from .data_insert import DataInsertApp
from .data_initdb import DataInitDBApp
from .user_auth import UserAuthApp
from .user_facility import UserFacilityApp


SUB_COMMANDS = {
    'app.pipeline': PipelineApp,
    'service.stream': StreamApp,
    'service.webapi': WebAPIApp,
    'data.select': DataSelectApp,
    'data.insert': DataInsertApp,
    'data.initdb': DataInitDBApp,
    'user.auth': UserAuthApp,
    'user.facility': UserFacilityApp,
}

PROGRAM = __appname__

USAGE = f"""\
usage: {__appname__} [<group>[.<command>]] [<args>...]
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
Applets defined within REFITT's framework.

commands:
    app
        .forecast      Build forecast for single candidate.
        .recommend     Build recommendations from forecasts.
        .pipeline      {PipelineApp.__doc__}
"""

SERVICE_GROUP = f"""\
Services run by "refittd".

commands:
    service
        .message       Message broker streaming service.
        .cluster       HPC job scheduling.
        .webapi        {WebAPIApp.__doc__}
        .stream        {StreamApp.__doc__}
"""

JOB_GROUP = f"""\
Manually manage REFITT batch computing tasks.

commands:
    job
        .submit        Submit jobs to the cluster.
        .delete        Delete jobs from the cluster.
        .status        Check the status of existing jobs.
"""

DATA_GROUP = f"""\
Interact with the REFITT database.

commands:
    data
        .select        {DataSelectApp.__doc__}
        .insert        {DataInsertApp.__doc__}
        .initdb        {DataInitDBApp.__doc__}
"""

USER_GROUP = f"""\
Manage user credentials and facility profiles.

commands:
    user
        .facility      {UserFacilityApp.__doc__}
        .auth          {UserAuthApp.__doc__}
"""

GROUPS = {
    'app':      APP_GROUP,
    'service':  SERVICE_GROUP,
    'job':      JOB_GROUP,
    'data':     DATA_GROUP,
    'user':     USER_GROUP,

}

GROUP_HELP = """\
usage: {name}.<command> [--help] [<args>...]

{info}\
"""

GROUP_DESC = {
    name: text.strip().split('\n')[0]
    for name, text in GROUPS.items()
}

HELP = f"""\
{USAGE}

groups:
    app               {GROUP_DESC['app']}
    service           {GROUP_DESC['service']}
    job               {GROUP_DESC['job']}
    data              {GROUP_DESC['data']}
    user              {GROUP_DESC['user']}

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

Use the -h/--help flag with the above groups/commands to
learn more about their usage.

{EPILOG}\
"""


# initialize module level logger
log = Logger.with_name(__appname__)


class CompletedCommand(Exception):
    """Lift exit_status of sub-commands `main` method."""


class Refitt(Application):
    """Application class for primary Refitt console-app."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('--version', version=__version__, action='version')

    subcommand: str = None
    interface.add_argument('subcommand')

    exceptions = {
        # extract exit status from exception arguments
        CompletedCommand: (lambda exc: int(exc.args[0])),
    }

    def run(self) -> None:
        """Show usage/help/version or defer to subcommand."""

        try:
            if self.subcommand in GROUPS.keys():
                print(GROUP_HELP.format(name=f'{__appname__} {self.subcommand}',
                                        info=GROUPS[self.subcommand]))
            else:
                status = SUB_COMMANDS[self.subcommand].main(sys.argv[2:])
                raise CompletedCommand(status)

        except KeyError as error:
            cmd, = error.args
            raise ArgumentError(f'"{cmd}" is not an available subcommand.')


def main() -> int:
    """Entry-point for `refitt` console application."""
    return Refitt.main(sys.argv[1:2])  # only first argument if present
