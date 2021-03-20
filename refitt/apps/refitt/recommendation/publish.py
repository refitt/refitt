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

"""Create recommendations and groups."""


# type annotations
from __future__ import annotations
from typing import Tuple, List, Dict, Union, Optional, Callable, IO

# standard libs
import os
import sys
import logging
from functools import partial, cached_property, wraps

# internal libs
from ....core.exceptions import log_exception
from ....database.model import (Recommendation, RecommendationGroup, RecommendationTag,
                                User, Facility, Forecast, Object, NotFound, )

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from pandas import DataFrame, read_csv, read_json, read_hdf
from sqlalchemy.exc import IntegrityError


PROGRAM = 'refitt recommendation publish'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} --group [--print]
       {PROGRAM} --user ID [--group ID] [--facility ID] --object ID --forecast ID --priority NUM [--print]
       {PROGRAM} [--from-file [PATH] [--csv | --json | --hdf5]] [--group ID] [--print]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --group     ID    Group ID for recommendation(s).
    --user      ID    User ID for recommendation.
    --facility  ID    Facility ID for recommendation.
    --object    ID    Object ID for recommendation.
    --priority  NUM   Priority value for recommendation.
    --forecast  ID    Forecast ID for recommendation.
    --print           Write ID of generated resources to <stdout>.
-h, --help            Show this message and exit.

If invoked with only --group, a new recommendation group will be created.
The output will be the new recommendation group ID.

Create a single recommendation by specifying a --user and all the necessary
values inline using the named options. The --user and --facility options may
be specified as alias and name, respectively, instead of their ID. If --group
is not specified, the most recent group is used. If --facility is not specified
and only one facility is registered for that user it will be used.

Create a set of recommendations at once by using --from-file. If no PATH is 
specified, read from standard input. Format is derived from file name extension, 
unless reading from standard input for which a format specifier (e.g., --csv) 
is required.\
"""


# application logger
log = logging.getLogger('refitt')


FILE_SCHEMA: Dict[str, type] = {
    'object_id': int,
    'user_id': int,
    'facility_id': int,
    'forecast_id': int,
    'priority': int,
}


Loader = Callable[[Union[str, IO]], DataFrame]
def check_schema(loader: Loader) -> Loader:
    """Wrapper method to check column names and types."""

    @wraps(loader)
    def wrapped_loader(file: Union[str, IO]) -> DataFrame:
        name = file if isinstance(file, str) else file.name
        data = loader(file)
        for column in data.columns:
            if column not in FILE_SCHEMA:
                raise RuntimeError(f'From file ({name}): unexpected column \'{column}\' in data file')
        for column, dtype in FILE_SCHEMA.items():
            if column not in data.columns:
                raise RuntimeError(f'From file ({name}): expected column \'{column}\' in data file')
            else:
                try:
                    data[column] = data[column].astype(dtype)
                except ValueError as error:
                    raise RuntimeError(f'From file ({name}), column \'{column}\': {error}') from error
        return data

    return wrapped_loader


class RecommendationPublishApp(Application):
    """Application class for recommendation and group creation."""

    interface = Interface(PROGRAM, USAGE, HELP)

    group: Optional[Union[bool, int]] = None
    interface.add_argument('--group', nargs='?', type=int, const=True, default=None)

    user: Optional[str] = None
    interface.add_argument('--user', default=None)

    facility: Optional[str] = None
    interface.add_argument('--facility', default=None)

    object: Optional[str] = None
    interface.add_argument('--object', default=None)

    priority: Optional[int] = None
    interface.add_argument('--priority', type=int, default=None)

    forecast: Optional[int] = None
    interface.add_argument('--forecast', type=int, default=None)

    file_path: Optional[str] = None
    interface.add_argument('--from-file', nargs='?', const='-', default=None, dest='file_path')

    format_csv: bool = False
    format_json: bool = False
    format_hdf5: bool = False
    io_interface = interface.add_mutually_exclusive_group()
    io_interface.add_argument('--csv', action='store_true', dest='format_csv')
    io_interface.add_argument('--json', action='store_true', dest='format_json')
    io_interface.add_argument('--hdf5', action='store_true', dest='format_hdf5')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        ArgumentError: partial(log_exception, logger=log.critical,
                               status=exit_status.bad_argument),
        FileNotFoundError: partial(log_exception, logger=log.critical,
                                   status=exit_status.bad_argument),
        IOError: partial(log_exception, logger=log.critical,
                         status=exit_status.bad_argument),
        NotFound: partial(log_exception, logger=log.critical,
                          status=exit_status.runtime_error),
        RuntimeError: partial(log_exception, logger=log.critical,
                              status=exit_status.runtime_error),
        IntegrityError: partial(log_exception, logger=log.critical,
                                status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Business logic of command."""
        if self.group_mode:
            return self.create_group()
        if self.file_mode:
            return self.create_from_file()
        else:
            self.check_missing_values()
            return self.create_from_values()

    @cached_property
    def group_mode(self) -> True:
        """Check if we are in group creation mode."""
        if self.group is None or self.group is not True:
            return False
        if any((self.user, self.facility, self.object, self.priority, self.forecast)):
            raise ArgumentError('--group without arguments suggestions group creation, but discrete values provided')
        if any((self.file_path, self.format_csv, self.format_json, self.format_hdf5)):
            raise ArgumentError('--group without arguments suggestions group creation, but file/format specified')
        return True

    @cached_property
    def file_mode(self) -> bool:
        """Check if we should be creating recommendations from a file."""
        if self.file_path is not None:
            if not any((self.user, self.facility, self.object, self.priority, self.forecast)):
                return True
            else:
                raise ArgumentError('Cannot provide discrete values with --from-file')
        else:
            return False

    def check_missing_values(self) -> None:
        """Check if are creating a single recommendation."""
        for name in ('user', 'object', 'priority', 'forecast'):
            given = getattr(self, name)
            if not given:
                raise ArgumentError(f'Single recommendation mode: missing discrete --{name}')

    def create_group(self) -> None:
        """Create new recommendation group and print new group ID."""
        self.write(RecommendationGroup.new().id)

    def create_from_values(self) -> None:
        """Create a new recommendation with the given inputs and print its new ID."""
        data = self.build_recommendation(group_id=self.group_id, object_id=self.object_id, priority=self.priority,
                                         user_id=self.user_id, facility_id=self.facility_id,
                                         forecast_id=self.forecast_id)
        recommendation, = self.add_recommendations([data, ])
        self.write(recommendation.id)

    @staticmethod
    def build_recommendation(group_id: int, object_id: int, priority: int,
                             user_id: int, facility_id: int, forecast_id: int) -> Recommendation:
        return Recommendation.from_dict({
            'group_id': group_id, 'tag_id': RecommendationTag.get_or_create(object_id).id,
            'priority': priority, 'object_id': object_id, 'user_id': user_id, 'facility_id': facility_id,
            'forecast_id': forecast_id, 'predicted_observation_id': Forecast.from_id(forecast_id).observation.id,
        })

    @staticmethod
    def add_recommendations(data: List[Recommendation]) -> List[Recommendation]:
        """Add all constructed recommendations to the database."""
        return Recommendation.add_all([pre.to_dict() for pre in data])
        # we deconstruct as dictionaries to use `add_all` and a single transaction.
        # we demand recommendation is constructed to validate schema and dependencies.

    @cached_property
    def group_id(self) -> int:
        """Unique group ID for recommendation."""
        if self.group is None:
            log.debug('Group not specified, fetching latest')
            return RecommendationGroup.latest().id
        try:
            return int(self.group)
        except ValueError:
            raise ArgumentError('--group must be an integer if specified with --user')

    @cached_property
    def user_id(self) -> int:
        """Unique user ID for recommendation."""
        try:
            return int(self.user)
        except ValueError:
            log.debug('User was not integer, looking up by alias')
            return User.from_alias(self.user).id

    @cached_property
    def facility_id(self) -> int:
        """Unique facility ID for recommendation."""
        if not self.facility:
            log.debug('Facility not given, looking up by user')
            facilities = User.from_id(self.user_id).facilities()
            if len(facilities) == 1:
                return facilities[0].id
            if len(facilities) == 0:
                raise ArgumentError('User is not associated with any facilities')
            else:
                raise ArgumentError('Must specify facility if user is associated with more than one')
        try:
            return int(self.facility)
        except ValueError:
            log.debug('Facility was not integer, looking up by name')
            return Facility.from_name(self.facility).id

    @cached_property
    def object_id(self) -> int:
        """Unique object ID for recommendation."""
        try:
            return int(self.object)
        except ValueError:
            log.debug('Object was not integer, lookup up by tag name')
            return Object.from_alias(tag=self.object).id

    @cached_property
    def forecast_id(self) -> int:
        """Unique forecast ID for recommendation."""
        try:
            return int(self.forecast)
        except ValueError as error:
            raise ArgumentError('Forecast ID must be an integer') from error

    def create_from_file(self) -> None:
        """Create many recommendations by file."""
        if self.file_path == '-':
            data = self.load_from_stdin()
        else:
            data = self.load_from_local(self.file_path)
        recommendations = []
        for idx, row in data.iterrows():
            new = self.build_recommendation(**{**row.to_dict(), 'group_id': self.group_id})
            recommendations.append(new)
        for recommendation in self.add_recommendations(recommendations):
            self.write(recommendation.id)

    def load_from_stdin(self) -> DataFrame:
        """Load recommendation data from standard input."""
        if self.file_format in ('csv', 'json', ):
            return self.loaders[self.file_format](sys.stdin)
        else:
            raise IOError(f'Standard input not supported for \'{self.file_format}\' files')

    def load_from_local(self, filepath: str) -> DataFrame:
        """Load recommendation data from local `filepath`."""
        if os.path.exists(filepath):
            return self.loaders[self.file_format](filepath)
        else:
            raise FileNotFoundError(f'File does not exist: {filepath}')

    @cached_property
    def loaders(self) -> Dict[str, Loader]:
        """File load methods."""
        return {
            'csv': self.load_csv,
            'json': self.load_json,
            'hdf5': self.load_hdf5,
        }

    @staticmethod
    @check_schema
    def load_csv(filepath: str) -> DataFrame:
        """Load recommendation data from CSV filepath."""
        return read_csv(filepath)

    @staticmethod
    @check_schema
    def load_json(filepath: str) -> DataFrame:
        """Load recommendation data from JSON filepath."""
        return read_json(filepath, orient='records')

    @staticmethod
    @check_schema
    def load_hdf5(filepath: str) -> DataFrame:
        """Load recommendation data from HDF5 filepath."""
        return DataFrame(read_hdf(filepath))  # coerce type

    @cached_property
    def file_formats(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Available file formats."""
        return {
            'csv': (self.format_csv, ['csv', ]),
            'json': (self.format_json, ['json', ]),
            'hdf5': (self.format_hdf5, ['hdf5', 'h5', ]),
        }

    @cached_property
    def file_format(self) -> str:
        """Input file format."""
        for file_format, (specified, extensions) in self.file_formats.items():
            if specified:
                return file_format
        else:
            if self.file_path == '-':
                raise ArgumentError('Must specify file format for standard input')
        if '.' not in self.file_path:
            raise ArgumentError(f'Missing file extension for {self.file_path}')
        file_ext = os.path.splitext(self.file_path)[1].strip('.')
        for file_format, (specified, extensions) in self.file_formats.items():
            if file_ext in extensions:
                return file_format
        else:
            raise ArgumentError(f'Unrecognized file format \'{file_ext}\'')

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)
