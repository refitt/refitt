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

"""Manage user facility profiles."""

# type annotations
from typing import Tuple, Union

# standard libs
import os
import sys
import json

# internal libs
from ...database import user
from ...core.logging import logger
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface, ArgumentError
import pandas as pd


# program name is constructed from module file name
NAME = os.path.basename(__file__)[:-3].replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} get {{ID | NAME}} [--oneline]
       {PADDING} set [FILE]
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
-1, --oneline                Put output on one line.

-d, --debug                  Show debugging messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""


# initialize module level logger
log = logger.with_name(f'{__appname__}.{NAME}')


class UserFacilityApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    mode: str = None
    modes: Tuple[str] = ('get', 'set')
    interface.add_argument('mode', choices=modes)

    source: str = None
    filepath: str = None
    interface.add_argument('source', nargs='?', default=None) # required for "get"

    oneline: bool = False
    interface.add_argument('-1', '--oneline', action='store_true')

    debug: bool = False
    interface.add_argument('-d', '--debug', action='store_true')

    facility_id: int = None
    facility_name: str = None

    def run(self) -> None:
        """Top-level entry-point for get/set methods."""

        if self.debug:
            for handler in log.handlers:
                handler.level = log.levels[0]

        # dispatch to appropriate action
        getattr(self, self.mode)()

    def get(self) -> None:
        """Get facility profile."""

        if self.source is None:
            raise ArgumentError('ID or NAME is required for "get" request.')

        try:
            profile = user.get_facility(facility_id=int(self.source))
        except (ValueError, TypeError):
            profile = user.get_facility(facility_name=self.source)

        # re-construct simple profile with facility_id
        # the facility_id from the original field from `pandas` is not serializable
        # on records that have never been updated, the facility_id isn't in the facility_profile
        # so we can an error, thus the `int` coercion
        profile = {'facility_id': int(profile['facility_id']), **profile['facility_profile']}

        indent = 4 if self.oneline is False else None
        print(json.dumps(profile, indent=indent))

    def set(self) -> None:
        """Set facility profiles."""

        if self.source is None:
            # get profile from stdin
            # if facility_id is present, the profile will be altered
            user.set_facility(json.load(sys.stdin))
            return

        if self.source.endswith('.xlsx'):
            data = pd.read_excel(self.source)
        elif self.source.endswith('.csv'):
            data = pd.read_csv(self.source)
        else:
            _, ext = os.path.splitext(self.source)
            raise ArgumentError(f'"{ext}" is not a supported file type.')

        for _, profile in data.iterrows():
            user.set_facility(profile.to_dict())

# inherit docstring from module
UserFacilityApp.__doc__ = __doc__
