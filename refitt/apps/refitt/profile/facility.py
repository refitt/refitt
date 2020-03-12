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

"""Manage facility profiles."""

# type annotations
from __future__ import annotations
from typing import Tuple

# standard libs
import os
import sys
import json
import functools

# internal libs
from .... import database
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, SYSLOG_HANDLER
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
import pandas as pd


# program name is constructed from module file name
PROGRAM = f'{__appname__} profile facility'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} get {{ID | NAME}} [--oneline] [--debug | --verbose] [--syslog]
       {PADDING} set [FILE] [--debug | --verbose] [--syslog]
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
ID                           ID of facility.
NAME                         Name of facility.
FILE                         Path to file with facility data.

options:
-1, --oneline                Put output on one line (only for "get").
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = Logger.with_name('.'.join(PROGRAM.split()))


class Facility(Application):
    """Manage facility profiles."""

    interface = Interface(PROGRAM, USAGE, HELP)

    mode: str = None
    modes: Tuple[str] = ('get', 'set')
    interface.add_argument('mode', choices=modes)

    source: str = None
    filepath: str = None
    interface.add_argument('source', nargs='?', default=None)  # required for "get"

    oneline: bool = False
    interface.add_argument('-1', '--oneline', action='store_true')

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

    facility_id: int = None
    facility_name: str = None

    def run(self) -> None:
        """Delegate to get/set methods."""
        run_ = getattr(self, self.mode)
        run_()

    def get(self) -> None:
        """Get facility profile."""

        if self.source is None:
            raise ArgumentError('ID or NAME is required for "get" request.')

        try:
            profile = database.user.get_facility(facility_id=int(self.source))
        except (ValueError, TypeError):
            profile = database.user.get_facility(facility_name=self.source)

        # re-construct simple profile with facility_id
        # the facility_id from the original field from `pandas` is not serializable
        # on records that have never been updated, the facility_id isn't in the facility_profile
        # so we can get an error, thus the `int` coercion
        profile = {'facility_id': int(profile['facility_id']), **profile['facility_profile']}

        indent = 4 if self.oneline is False else None
        print(json.dumps(profile, indent=indent))

    def set(self) -> None:
        """Set facility profiles."""

        if self.source is None:
            # get profile from stdin
            # if facility_id is present, the profile will be altered
            database.user.set_facility(json.load(sys.stdin))
            return

        if self.source.endswith('.xlsx'):
            data = pd.read_excel(self.source)
        elif self.source.endswith('.csv'):
            data = pd.read_csv(self.source)
        else:
            _, ext = os.path.splitext(self.source)
            raise ArgumentError(f'"{ext}" is not a supported file type.')

        for _, profile in data.iterrows():
            database.user.set_facility(profile.to_dict())

    def __enter__(self) -> Facility:
        """Initialize resources."""

        if self.syslog:
            log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        elif self.verbose:
            log.handlers[0].level = log.levels[1]
        else:
            log.handlers[0].level = log.levels[2]

        # persistent connection
        database.connect()
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
