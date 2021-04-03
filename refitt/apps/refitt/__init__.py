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

"""Entry-point for refitt command-line interface."""


# standard libs
import sys
import logging

# internal libs
from ...__meta__ import (__version__, __description__,
                         __copyright__, __developer__, __contact__,
                         __website__, __ascii_art__)
from . import config, database, service, auth, login, whoami, api, notify, recommendation, forecast

# external libs
from cmdkit.app import Application, ApplicationGroup
from cmdkit.cli import Interface


PROGRAM = 'refitt'
USAGE = f"""\
usage: {PROGRAM} [-h] [-v] <command> [<args>...]
{__description__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} <{__contact__}>\
"""

HELP = f"""\
{USAGE}

commands:
auth                   {auth.__doc__}
login                  {login.__doc__}
whoami                 {whoami.__doc__}
api                    {api.__doc__}
config                 {config.__doc__}
database               {database.__doc__}
service                {service.__doc__}
notify                 {notify.__doc__}
forecast               {forecast.__doc__}
recommendation         {recommendation.__doc__}
pipeline               ...

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

Use the -h/--help flag with the above commands to
learn more about their usage.

{EPILOG}\
"""


# initialize application logger
log = logging.getLogger('refitt')


# logging setup for command-line interface
Application.log_critical = log.critical
Application.log_exception = log.exception


class RefittApp(ApplicationGroup):
    """Top-level application class for Refitt."""

    interface = Interface(PROGRAM, USAGE, HELP)
    interface.add_argument('command')
    interface.add_argument('-v', '--version', action='version', version=__version__)
    interface.add_argument('--ascii-art', action='version', version=__ascii_art__)

    command = None
    commands = {'auth': auth.AuthApp,
                'login': login.LoginApp,
                'whoami': whoami.WhoAmIApp,
                'api': api.WebApp,
                'config': config.ConfigApp,
                'database': database.DatabaseApp,
                'service': service.ServiceApp,
                'notify': notify.NotifyApp,
                'forecast': forecast.ForecastApp,
                'recommendation': recommendation.RecommendationApp,
                }


def main() -> int:
    """Entry-point for `refitt` console application."""
    return RefittApp.main(sys.argv[1:])
