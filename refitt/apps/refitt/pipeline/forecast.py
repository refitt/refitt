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

"""Run forecast on candidate."""

# type annotations
from __future__ import annotations

# standard libs
import functools

# internal libs
from ....core.logging import Logger, cli_setup
from ....core.exceptions import log_and_exit
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
PROGRAM = f'{__appname__} pipeline forecast'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <source> [--output-directory PATH]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

arguments:
<source>                       Path to candidates file.

options:
-o, --output-directory  PATH   Directory for output files.
-d, --debug                    Show debugging messages.
-v, --verbose                  Show information messages.
    --syslog                   Use syslog style messages.
-h, --help                     Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger(__name__)


class Forecast(Application):
    """Run forecast on candidate."""

    interface = Interface(PROGRAM, USAGE, HELP)

    # input file containing list of candidates/alerts
    source: str = '-'
    interface.add_argument('source')

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Run Refitt pipeline."""
        raise RuntimeError('not implemented')

    def __enter__(self) -> Forecast:
        """Initialize resources."""
        cli_setup(self)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
