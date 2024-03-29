# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Publish recommendations."""


# type annotations
from __future__ import annotations
from typing import Tuple, List, Dict, Union, Optional, Callable, IO

# standard libs
import os
import sys
from functools import partial, cached_property, wraps

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError
from pandas import DataFrame, read_csv, read_json, read_hdf

# internal libs
from refitt.core import typing
from refitt.core.exceptions import handle_exception
from refitt.core.logging import Logger
from refitt.database.model import (Recommendation, Epoch, RecommendationTag, Observation,
                                   User, Facility, Object, NotFound, )

# public interface
__all__ = ['RecommendationPublishApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt recommendation publish'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} --user ID --priority NUM (--object ID | --prediction ID) [--epoch ID] [--facility ID] [--print]
       {PROGRAM} [--from-file [PATH] [--csv | --json | --hdf5]] [--epoch ID] [--print]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
    --user          ID    User ID for recommendation.
    --epoch         ID    Epoch ID for recommendation(s) (default <latest>).
    --facility      ID    Facility ID for recommendation.
    --object        ID    Object ID for recommendation.
    --prediction    ID    Observation ID for prediction.
    --priority      NUM   Priority value for recommendation.
    --print               Write ID of generated resources to <stdout>.
    --extra-fields        NAME[=TYPE] [NAME[=TYPE] ...] (extra fields to pull into 'data').
    --from-file     PATH  File path for bulk recommendations.
    --csv                 Specify file format as CSV.
    --json                Specify file format as JSON.
    --hdf5                Specify file format as HDF5.
-h, --help                Show this message and exit.

Create a single recommendation by specifying a --user and all the necessary
values inline with the named options. The --user and --facility options may
be specified as alias or name, respectively, instead of their ID. If --epoch
is not specified, the most recent epoch is used. If --facility is not specified
and only one facility is registered for that user it will be used.

Publish a large batch of recommendations using --from-file. If no PATH is 
specified, read from standard input. Format is derived from the file extension, 
unless reading from standard input for which a format specifier (e.g., --csv) 
is required.

The --extra-fields option allows additional columns from a file or extra fields
in single recommendation mode. Ordinarily, additional columns would be ignored.
In file mode, the value (e.g., '--extra-fields maxalt[=int]') is the data type.
In single recommendation mode, it is the discrete value 
(e.g., '--extra-fields maxalt=42).\
"""


REQUIRED_FIELDS = ['object_id', 'user_id', 'facility_id', 'priority', 'prediction_id']
FILE_SCHEMA = {
    'object_id': int,
    'user_id': int,
    'facility_id': int,
    'priority': int,
    'prediction_id': int,
}


# type annotation for loader function
LoaderImpl = Callable[[Union[str, IO], Optional[Dict[str, str]]], DataFrame]


def check_schema(loader_impl: LoaderImpl) -> LoaderImpl:
    """Wrapper method to check column names and types."""

    @wraps(loader_impl)
    def wrapped_loader(fp: Union[str, IO], extra_fields: Dict[str, str] = None) -> DataFrame:
        name = fp if isinstance(fp, str) else fp.name
        data = loader_impl(fp, extra_fields)
        schema = FILE_SCHEMA if not extra_fields else {**FILE_SCHEMA, **extra_fields}
        for column in list(data.columns):
            if column not in schema:
                log.info(f'From file ({name}): ignoring column \'{column}\'')
                data.drop([column], axis=1, inplace=True)
        for column, dtype in schema.items():
            if column not in data.columns:
                raise RuntimeError(f'From file ({name}): missing column \'{column}\'')
            else:
                try:
                    data[column] = data[column].astype(dtype)
                except (TypeError, ValueError) as error:
                    raise RuntimeError(f'From file ({name}), column \'{column}\': {error}') from error
        return data

    return wrapped_loader


class RecommendationPublishApp(Application):
    """Application class for recommendation publishing."""

    interface = Interface(PROGRAM, USAGE, HELP)

    epoch: Optional[int] = None
    interface.add_argument('--epoch', type=int, default=None)

    user: Optional[str] = None
    interface.add_argument('--user', default=None)

    facility: Optional[str] = None
    interface.add_argument('--facility', default=None)

    object: Optional[str] = None
    interface.add_argument('--object', default=None)

    prediction: Optional[int] = None
    interface.add_argument('--prediction', type=int, default=None)

    priority: Optional[int] = None
    interface.add_argument('--priority', type=int, default=None)

    file_path: Optional[str] = None
    interface.add_argument('--from-file', nargs='?', const='-', default=None, dest='file_path')

    format_csv: bool = False
    format_json: bool = False
    format_hdf5: bool = False
    io_interface = interface.add_mutually_exclusive_group()
    io_interface.add_argument('--csv', action='store_true', dest='format_csv')
    io_interface.add_argument('--json', action='store_true', dest='format_json')
    io_interface.add_argument('--hdf5', action='store_true', dest='format_hdf5')

    extra_fields_args: str = []
    interface.add_argument('--extra-fields', nargs='+', default=[], dest='extra_fields_args')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        FileNotFoundError: partial(handle_exception, logger=log,
                                   status=exit_status.bad_argument),
        IOError: partial(handle_exception, logger=log,
                         status=exit_status.bad_argument),
        NotFound: partial(handle_exception, logger=log,
                          status=exit_status.runtime_error),
        IntegrityError: partial(handle_exception, logger=log,
                                status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Business logic of command."""
        if self.file_mode:
            self.create_from_file()
        else:
            self.check_missing_values()
            self.create_from_values()

    @cached_property
    def extra_fields(self) -> Dict[str, typing.ValueType]:
        """Build extra fields dictionary with type names for values."""
        if self.file_mode:
            return self.__extra_fields_with_types()
        else:
            return self.__extra_fields_with_values()

    def __extra_fields_with_types(self) -> Dict[str, str]:
        """Extra fields specified with type names for values (default with 'str')."""
        extra_fields = {}
        for field in self.extra_fields_args:
            name = field
            value = 'str'
            if '=' in field:
                name, value = field.split('=')
            extra_fields[name.strip()] = value.strip()
        return extra_fields

    def __extra_fields_with_values(self) -> Dict[str, typing.ValueType]:
        """Extra fields specified with discrete values (no default)."""
        extra_fields = {}
        for field in self.extra_fields_args:
            if '=' in field:
                name, value = field.split('=')
                extra_fields[name.strip()] = value.strip()
            else:
                raise ArgumentError('Missing required assignment in \'{field}\', from --extra-fields')
        return {field: typing.coerce_json(value) for field, value in extra_fields.items()}

    @cached_property
    def file_mode(self) -> bool:
        """Check if we should be creating recommendations from a file."""
        if self.file_path is not None:
            if not any((self.user, self.facility, self.object, self.priority, self.prediction)):
                return True
            else:
                raise ArgumentError('Cannot provide discrete values with --from-file')
        else:
            return False

    def check_missing_values(self) -> None:
        """Check if are creating a single recommendation."""
        for name in ('user', 'priority'):
            given = getattr(self, name)
            if not given:
                raise ArgumentError(f'Single recommendation mode: missing discrete --{name}')

    def create_from_values(self) -> None:
        """Create a new recommendation with the given inputs and print its new ID."""
        rec = self.build_recommendation(epoch_id=self.epoch_id, object_id=self.object_id, priority=self.priority,
                                        prediction_id=self.prediction_id, user_id=self.user_id,
                                        facility_id=self.facility_id, **self.extra_fields)
        recommendation, = self.add_recommendations([rec, ])
        self.write(recommendation.id)

    @staticmethod
    def build_recommendation(epoch_id: int, object_id: int, priority: int, user_id: int, facility_id: int,
                             prediction_id: int, **data) -> Recommendation:
        return Recommendation.from_dict({
            'epoch_id': epoch_id, 'tag_id': RecommendationTag.get_or_create(object_id).id,
            'priority': priority, 'object_id': object_id, 'user_id': user_id, 'facility_id': facility_id,
            'predicted_observation_id': prediction_id,
            'data': data
        })

    @staticmethod
    def add_recommendations(data: List[Recommendation]) -> List[Recommendation]:
        """Add all constructed recommendations to the database."""
        # Note: We deconstruct as dictionaries to use `add_all` and a single transaction.
        #       We demand recommendation is constructed to validate schema and dependencies.
        return Recommendation.add_all([pre.to_dict() for pre in data])

    @cached_property
    def epoch_id(self) -> int:
        """Unique epoch ID for recommendation."""
        if self.epoch is None:
            log.debug('Epoch not specified, fetching latest')
            return Epoch.latest().id
        try:
            return int(self.epoch)
        except ValueError:
            raise ArgumentError('--epoch must be an integer if specified')

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
    def object_id(self) -> Optional[int]:
        """Unique object ID for recommendation."""
        if not self.object:
            if self.prediction_id:
                return Observation.from_id(self.prediction_id).id
            else:
                raise ArgumentError(f'Must specify at least one of --object or --prediction')
        try:
            return int(self.object)
        except ValueError:
            log.debug('Object was not integer, lookup up by name')
            return Object.from_name(self.object).id

    @cached_property
    def prediction_id(self) -> Optional[int]:
        """Unique observation ID for prediction (from forecast models)."""
        if not self.prediction:
            return None
        try:
            return int(self.prediction)
        except ValueError as error:
            raise ArgumentError('Observation ID for --prediction must be an integer') from error

    def create_from_file(self) -> None:
        """Create many recommendations by file."""
        if self.file_path == '-':
            data = self.load_from_stdin()
        else:
            data = self.load_from_local(self.file_path)
        recommendations = []
        for idx, row in data.iterrows():
            new = self.build_recommendation(**{**row.to_dict(), 'epoch_id': self.epoch_id})
            recommendations.append(new)
        for recommendation in self.add_recommendations(recommendations):
            self.write(recommendation.id)

    def load_from_stdin(self) -> DataFrame:
        """Load recommendation data from standard input."""
        if self.file_format in ('csv', 'json', ):
            return self.loaders[self.file_format](sys.stdin, self.extra_fields)
        else:
            raise IOError(f'Standard input not supported for \'{self.file_format}\' files')

    def load_from_local(self, filepath: str) -> DataFrame:
        """Load recommendation data from local `filepath`."""
        if os.path.exists(filepath):
            return self.loaders[self.file_format](filepath, self.extra_fields)
        else:
            raise FileNotFoundError(f'File does not exist: {filepath}')

    @cached_property
    def loaders(self) -> Dict[str, LoaderImpl]:
        """File load methods."""
        return {
            'csv': self.load_csv,
            'json': self.load_json,
            'hdf5': self.load_hdf5,
        }

    @staticmethod
    @check_schema
    def load_csv(fp: Union[str, IO], extra_fields: Dict[str, str] = None) -> DataFrame:  # noqa: extra_fields unused
        """Load recommendation data from CSV filepath/descriptor."""
        return read_csv(fp)

    @staticmethod
    @check_schema
    def load_json(fp: Union[str, IO], extra_fields: Dict[str, str] = None) -> DataFrame:  # noqa: extra_fields unused
        """Load recommendation data from JSON filepath/descriptor."""
        return read_json(fp, orient='records')

    @staticmethod
    @check_schema
    def load_hdf5(fp: str, extra_fields: Dict[str, str] = None) -> DataFrame:  # noqa: extra_fields unused
        """Load recommendation data from HDF5 filepath."""
        return DataFrame(read_hdf(fp))  # NOTE: coerce type

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
