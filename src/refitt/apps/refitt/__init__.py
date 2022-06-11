# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Entry-point for refitt command-line interface."""


# standard libs
import sys
import functools

# external libs
from cmdkit.app import Application, ApplicationGroup, exit_status
from cmdkit.cli import Interface
from cmdkit.config import ConfigurationError

# internal libs
from refitt import __version__, __developer__, __contact__, __website__, __copyright__, __description__, __ascii_art__
from refitt.core.exceptions import handle_exception, write_traceback
from refitt.core.logging import Logger

# public interface
__all__ = ['RefittApp', 'main', ]

# application logger
log = Logger.with_name('refitt')


# logging setup for command-line interface
Application.log_critical = log.critical
Application.log_exception = log.exception
Application.exceptions = {
    **Application.exceptions,
    ConfigurationError: functools.partial(handle_exception, logger=log, status=exit_status.bad_config),
    RuntimeError: functools.partial(handle_exception, logger=log, status=exit_status.runtime_error),
    Exception: functools.partial(write_traceback, logger=log),
}


# logging setup for command-line interface
ApplicationGroup.log_critical = log.critical
ApplicationGroup.log_exception = log.exception
ApplicationGroup.exceptions = {
    **ApplicationGroup.exceptions,
    ConfigurationError: functools.partial(handle_exception, logger=log, status=exit_status.bad_config),
    RuntimeError: functools.partial(handle_exception, logger=log, status=exit_status.runtime_error),
    Exception: functools.partial(write_traceback, logger=log),
}


# NOTE: delayed imports to allow Application class modifications
from refitt.apps.refitt import (config, database, service, auth, login, whoami, api, notify,
                                recommendation, forecast, object, epoch)  # noqa


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
  user:
      login                  {login.__doc__}
      whoami                 {whoami.__doc__}
      api                    {api.__doc__}
      config                 {config.__doc__}

  admin:
      auth                   {auth.__doc__}
      database               {database.__doc__}
      object                 {object.__doc__}
      service                {service.__doc__}

  workflows:
      epoch                  {epoch.__doc__}
      notify                 {notify.__doc__}
      forecast               {forecast.__doc__}
      recommendation         {recommendation.__doc__}
      pipeline               ...

options:
-h, --help                   Show this message and exit.
-v, --version                Show the version and exit.
    --ascii-art              Show ascii art and exit.

{EPILOG}\
"""


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
                'api': api.APIClientApp,
                'config': config.ConfigApp,
                'database': database.DatabaseApp,
                'epoch': epoch.EpochApp,
                'service': service.ServiceApp,
                'notify': notify.NotifyApp,
                'object': object.QueryObjectApp,
                'forecast': forecast.ForecastApp,
                'recommendation': recommendation.RecommendationApp,
                }


def main() -> int:
    """Entry-point for `refitt` console application."""
    return RefittApp.main(sys.argv[1:])
