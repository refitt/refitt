# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Publish observation data."""


# type annotations
from __future__ import annotations
from typing import TextIO, Tuple

# standard libs
import os
import sys
from datetime import datetime
from functools import partial, cached_property

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError
from astropy.time import Time
from astropy.io import fits

# internal libs
from refitt.core.logging import Logger
from refitt.core.exceptions import handle_exception
from refitt.web.api.endpoint.recommendation import FILE_SIZE_LIMIT
from refitt.database.model import (Observation, ObservationType, Object, Epoch, Source, Recommendation,
                                   File, FileType)
from refitt.database.core import NotFound

# public interface
__all__ = ['ObservationPublishApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt observation publish'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} [-h] SOURCE OBJECT BAND MAG ERR [MJD] [-r ID] [-f FILE] 
       {PADDING} [--epoch ID] [--print] [--force]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
SOURCE                      Name or ID of source (user and facility info).
OBJECT                      Name, tag, or ID of object (e.g., ZTFabs2022af).
BAND                        Name of filter band (e.g., r-ztf).
MAG                         Final magnitude value (e.g., 20.14).
ERR                         Error in magnitude value (e.g., 0.12).
MJD                         MJD of observation (pulled from file if available).

options:
-r, --recommendation  ID    ID of corresponding recommendation.
-f, --file            FILE  Path to reduced file (e.g., FITS).
    --epoch           ID    Epoch for observation (default <latest>).
    --print                 Write ID of created observation record to <stdout>.
    --force                 Force overwrite of observation
-h, --help                  Show this message and exit.\
"""


class ObservationPublishApp(Application):
    """Application class for observation publishing."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source_name: str
    interface.add_argument('source_name', metavar='SOURCE')

    object_name: str
    interface.add_argument('object_name', metavar='OBJECT')

    band_name: str
    interface.add_argument('band_name', metavar='BAND')

    mag_value: float
    interface.add_argument('mag_value', type=float, metavar='MAG')

    err_value: float
    interface.add_argument('err_value', type=float, metavar='ERR')

    mjd_value: float = None
    interface.add_argument('mjd_value', type=float, nargs='?', default=None, metavar='MJD')

    recommendation_id: int = None
    interface.add_argument('-r', '--recommendation', dest='recommendation_id', type=int)

    epoch_id: int = None
    interface.add_argument('--epoch', dest='epoch_id', type=int)

    file_path: str = None
    interface.add_argument('-f', '--file', dest='file_path')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    force: bool = False
    interface.add_argument('--force', action='store_true')

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
        epoch = self.get_epoch()
        source = self.get_source()
        object = self.get_object()
        if self.recommendation_id:
            recommendation = self.get_recommendation(source)
        else:
            recommendation = None
        if self.file_path:
            file_basename, file_type = self.load_file()
        else:
            file_basename, file_type = None, None
        if not self.mjd_value:
            raise ArgumentError('No MJD provided')
        observation = self.publish_observation(epoch, object, source)
        if recommendation is not None:
            log.info(f'Updating recommendation ({recommendation.id}) with observation ({observation.id})')
            Recommendation.update(recommendation.id, observation_id=observation.id)
        if self.file_path:
            log.info(f'Uploading file ({file_basename})')
            with open(self.file_path, mode='rb') as stream:
                File.add({'observation_id': observation.id, 'epoch_id': epoch.id, 'name': file_basename,
                          'type_id': FileType.from_name(file_type).id, 'data': stream.read()})
        self.write(observation.id)

    def get_epoch(self: ObservationPublishApp) -> Epoch:
        """Look up epoch in database."""
        if self.epoch_id:
            epoch = Epoch.from_id(self.epoch_id)
        else:
            epoch = Epoch.latest()
            log.info(f'Latest epoch ({epoch.id}: {epoch.created})')
        return epoch

    def get_source(self: ObservationPublishApp) -> Source:
        """Look up source in database."""
        if self.source_name.isdigit():
            source = Source.from_id(int(self.source_name))
        else:
            source = Source.from_name(self.source_name)
            log.info(f'Resolved source ({source.id}: {source.name})')
        return source

    def get_object(self: ObservationPublishApp) -> Object:
        """Look up object in database."""
        object = Object.from_name(self.object_name)
        log.info(f'Resolved object ({object.id}: {self.object_name})')
        return object

    def get_recommendation(self: ObservationPublishApp, source: Source) -> Recommendation:
        """Look up associated recommendation in database."""
        recommendation = Recommendation.from_id(self.recommendation_id)
        if recommendation.user_id != source.user_id:
            raise RuntimeError(f'Recommendation ({self.recommendation_id}) not owned by '
                               f'user ({source.user_id}) from source ({self.source_name})')
        if recommendation.facility_id != source.facility_id:
            raise RuntimeError(f'Recommendation ({self.recommendation_id}) not associated with '
                               f'facility ({source.facility_id}) from source ({self.source_name})')
        if recommendation.observation_id and not self.force:
            raise RuntimeError(f'Recommendation ({self.recommendation_id}) already has an '
                               f'observation ({recommendation.observation_id})')
        return recommendation

    def load_file(self: ObservationPublishApp) -> Tuple[str, str]:
        """Inspect file and load data."""
        if not os.path.isfile(self.file_path):
            raise RuntimeError(f'File does not exist ({self.file_path})')
        if os.path.getsize(self.file_path) > FILE_SIZE_LIMIT:
            raise RuntimeError(f'File exceeds maximum allowed size ({self.file_path})')
        file_basename = os.path.basename(self.file_path)
        file_type = os.path.splitext(file_basename)[1].lower().strip()
        if file_type in ('.gz', '.xz', '.bz2'):  # Take one more if compression format
            file_type = os.path.splitext(file_basename[:-len(file_type)])[1].lower().strip() + file_type
        file_type = file_type.lstrip('.')
        allowed_types = [ft.name.lower() for ft in FileType.load_all()]
        if file_type not in allowed_types:
            raise RuntimeError(f'File type not allowed ({file_type})')
        if not self.mjd_value:
            header_dateobs = None
            with fits.open(self.file_path) as hdulist:
                if 'DATE-OBS' in hdulist[0].header:
                    header_dateobs = hdulist[0].header['DATE-OBS']
                    self.mjd_value = Time(datetime.fromisoformat(header_dateobs)).mjd
                else:
                    raise RuntimeError(f'Missing DATE-OBS in header ({file_basename})')
            log.info(f'Extracted MJD ({header_dateobs}) from file ({self.file_path})')
        return file_basename, file_type

    def publish_observation(self, epoch: Epoch, object: Object, source: Source) -> Observation:
        """Publish observation to database."""
        observation = Observation.add({
            'type_id': ObservationType.from_name(self.band_name).id,
            'epoch_id': epoch.id,
            'object_id': object.id,
            'source_id': source.id,
            'value': self.mag_value,
            'error': self.err_value,
            'time': Time(self.mjd_value, format='mjd', scale='utc').datetime,
            'recorded': datetime.now().astimezone(),
        })
        log.info(f'Published observation ({observation.id})')
        return observation

    @cached_property
    def output(self) -> TextIO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)
