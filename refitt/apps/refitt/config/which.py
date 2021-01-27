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

"""Check origin of configuration variable."""


# standard libs
import logging
from functools import partial

# internal libs
from ....core.config import PATH, config, ConfigurationError
from ....core.exceptions import log_exception

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


PROGRAM = 'refitt config which'
USAGE = f"""\
usage: {PROGRAM} [-h] SECTION[...].VAR
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
SECTION[...].VAR        Path to variable.

options:
-h, --help              Show this message and exit.\
"""


# application logger
log = logging.getLogger('refitt')


class WhichConfigApp(Application):
    """Application class for config which command."""

    interface = Interface(PROGRAM, USAGE, HELP)

    varpath: str = None
    interface.add_argument('varpath', metavar='VAR')

    exceptions = {
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        ConfigurationError: partial(log_exception, logger=log.critical,
                                    status=exit_status.bad_config),
    }

    def run(self) -> None:
        """Business logic for `config which`."""
        try:
            site = config.which(*self.varpath.split('.'))
        except KeyError:
            self.log_critical(f'"{self.varpath}" not found')
            return
        if site in ('default', 'env'):
            print(site)
        else:
            path = PATH[site].config
            print(f'{site}: {path}')
