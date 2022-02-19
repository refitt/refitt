# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) catalog interface."""


# type annotations
from __future__ import annotations
from typing import Union, IO, NamedTuple, Dict, TypeVar, Type

# standard libs
import os
import re
import logging
from io import BytesIO
from zipfile import ZipFile
from datetime import datetime, timedelta

# external libs
import numpy as np
from pandas import DataFrame, read_csv

# internal libs
from .interface import TNSInterface, TNSQueryCatalogResult, TNSError
from ...core.config import get_site

# public interface
__all__ = ['TNSCatalog', 'TNSRecord', ]


# initialize module level logger
log = logging.getLogger(__name__)


# object name provider pattern matching
OBJECT_NAMING_PATTERNS: Dict[str, re.Pattern] = {
    'ztf': re.compile(r'ZTF.*'),
    'iau': re.compile(r'20[2-3][0-9][a-zA-Z]+'),
    'antares': re.compile(r'ANT.*'),
    'atlas': re.compile(r'ATLAS.*'),
}


class TNSCatalogError(TNSError):
    """Exception specific to TNSCatalog interface."""


class TNSCatalog:
    """Interface for downloading and transforming TNS catalog data."""

    data: DataFrame
    last_updated: datetime = None
    interface: Type[TNSInterface] = TNSInterface

    def __init__(self, data: Union[TNSCatalog, DataFrame]) -> None:
        """Direct initialization with existing `data`."""
        self.data = data if isinstance(data, DataFrame) else data.data

    @classmethod
    def from_dataframe(cls, dataframe: DataFrame) -> TNSCatalog:
        """Initialize with existing `dataframe`."""
        return cls(dataframe)

    DEFAULT_EXPIRED_AFTER = timedelta(days=1)
    DEFAULT_CACHE_DIR = os.path.join(get_site().lib, 'tns')
    DEFAULT_CACHE_PATH = os.path.join(DEFAULT_CACHE_DIR, 'tns_public_objects.csv')

    @classmethod
    def remove_cache(cls) -> None:
        """Delete cached data if it exists."""
        if os.path.exists(cls.DEFAULT_CACHE_PATH):
            os.remove(cls.DEFAULT_CACHE_PATH)

    @classmethod
    def from_web(cls, cache: bool = True, expired_after: timedelta = DEFAULT_EXPIRED_AFTER) -> TNSCatalog:
        """Query TNS and return new catalog."""
        os.makedirs(cls.DEFAULT_CACHE_DIR, exist_ok=True)
        if cache and cls.__cache_valid(expired_after):
            log.info(f'Loading from cache: {cls.DEFAULT_CACHE_PATH}')
            self = cls.from_local(cls.DEFAULT_CACHE_PATH)
            self.last_updated = datetime.fromtimestamp(os.stat(cls.DEFAULT_CACHE_PATH).st_mtime)
            return self
        else:
            log.info(f'Fetching latest catalog')
            self = cls.from_query(cls.interface().search_catalog())
            self.last_updated = datetime.now()
            if cache:
                log.debug(f'Writing catalog to cache: {cls.DEFAULT_CACHE_PATH}')
                self.to_local(cls.DEFAULT_CACHE_PATH)
            return self

    @classmethod
    def __cache_valid(cls, expired_after: timedelta) -> bool:
        """Check cache file is expired or missing."""
        if not os.path.exists(cls.DEFAULT_CACHE_PATH):
            log.debug(f'Cache not found: {cls.DEFAULT_CACHE_PATH}')
            return False
        age = datetime.now() - datetime.fromtimestamp(os.stat(cls.DEFAULT_CACHE_PATH).st_mtime)
        if age > expired_after:
            log.debug(f'Cache expired ({age} > {expired_after})')
            return False
        else:
            return True

    @classmethod
    def from_query(cls, result: TNSQueryCatalogResult) -> TNSCatalog:
        """Build catalog from existing `requests.Response`."""
        return cls.from_zip(BytesIO(result.data))

    @classmethod
    def from_zip(cls, file_or_stream: Union[str, IO]) -> TNSCatalog:
        """Extract CSV data from inside Zip archive."""
        with ZipFile(file_or_stream) as archive:
            with archive.open('tns_public_objects.csv') as stream:
                return cls.from_local(BytesIO(stream.read()), skiprows=1)  # NOTE: first row is date of last change

    @classmethod
    def from_local(cls, file_or_stream: Union[str, IO], **options) -> TNSCatalog:
        """Read CSV formatted data from local file path or existing IO stream."""
        dtype = {'typeid': 'Int16', 'reporting_groupid': 'Int16', 'source_groupid': 'Int16'}
        dataframe = read_csv(file_or_stream, dtype=dtype, **options)
        dataframe.discoverydate = dataframe.discoverydate.astype('datetime64[ns]')
        dataframe.time_received = dataframe.time_received.astype('datetime64[ns]')
        dataframe.creationdate = dataframe.creationdate.astype('datetime64[ns]')
        dataframe.lastmodified = dataframe.lastmodified.astype('datetime64[ns]')
        dataframe.loc[dataframe.internal_names.isnull(), 'internal_names'] = ''
        self = cls.from_dataframe(dataframe)
        if isinstance(file_or_stream, str):
            self.last_updated = datetime.fromtimestamp(os.stat(file_or_stream).st_mtime)
        else:
            self.last_updated = datetime.now()
        return self

    def to_local(self, filepath: str, **options) -> None:
        """Write data to local disk at `filepath`."""
        self.data.to_csv(filepath, index=False, **options)  # noqa: stupid type annotations

    def refresh(self, expired_after: timedelta = DEFAULT_EXPIRED_AFTER) -> None:
        """Updates catalog if necessary."""
        age = datetime.now() - self.last_updated
        if age > expired_after:
            log.info(f'Catalog expired ({age} > {expired_after}')
            self.data = self.from_web(cache=False).data
            self.to_local(self.DEFAULT_CACHE_PATH)

    class NoRecordsFound(TNSCatalogError):
        """No records found for the given filters."""

    class MultipleRecordsFound(TNSCatalogError):
        """More than one record found for the given filters."""

    def get(self, name: str) -> TNSRecord:
        """Look up object by `name` in catalog."""
        for provider, pattern in OBJECT_NAMING_PATTERNS.items():
            if pattern.match(name):
                if provider == 'iau':
                    return self.__get_from_iau(name)
                else:
                    return self.__get_from_internal_names(name)
        else:
            raise self.NoRecordsFound(f'Unrecognized name pattern \'{name}\'')

    def __get_from_iau(self, name: str) -> TNSRecord:
        """Look up record against exact matching IAU `name`."""
        results = self.data.loc[self.data.name == name]
        results = results.where(results.notnull(), None).replace({np.nan: None})  # clean up NaN/NA
        if len(results) == 0:
            raise self.NoRecordsFound(f'No record with name == {name}')
        if len(results) == 1:
            return TNSRecord(**results.iloc[0].to_dict())
        else:
            raise self.MultipleRecordsFound(f'Multiple records with name == {name}')

    def __get_from_internal_names(self, name: str) -> TNSRecord:
        """Fuzzy match of `name` against `internal_names` list."""
        results = self.data.loc[self.data.internal_names.str.contains(name)]
        results = results.where(results.notnull(), None).replace({np.nan: None})  # clean up NaN/NA
        if len(results) == 0:
            raise self.NoRecordsFound(f'No record with object_names ~ {name}')
        if len(results) == 1:
            return TNSRecord(**results.iloc[0].to_dict())
        else:
            raise self.MultipleRecordsFound(f'Multiple records with object_names ~ {name}')


TNSValue = TypeVar('TNSValue', int, float, str)
class TNSRecord(NamedTuple):
    """A single record from the TNSCatalog."""

    objid: int
    name_prefix: str
    name: str
    ra: float
    declination: float
    redshift: float
    typeid: int
    type: str
    reporting_groupid: int
    reporting_group: str
    source_groupid: int
    source_group: str
    discoverydate: datetime
    discoverymag: float
    discmagfilter: str
    filter: str
    reporters: str
    time_received: datetime
    internal_names: str
    creationdate: datetime
    lastmodified: datetime

    def to_json(self) -> Dict[str, TNSValue]:
        """Format as dictionary with JSON-serializable types."""
        return {'objid': self.objid,
                'name_prefix': self.name_prefix,
                'name': self.name,
                'ra': self.ra,
                'declination': self.declination,
                'redshift': self.redshift,
                'typeid': self.typeid,
                'type': self.type,
                'reporting_groupid': self.reporting_groupid,
                'reporting_group': self.reporting_group,
                'source_groupid': self.source_groupid,
                'source_group': self.source_group,
                'discoverydate': str(self.discoverydate),
                'discoverymag': self.discoverymag,
                'discmagfilter': self.discmagfilter,
                'filter': self.filter,
                'reporters': self.reporters,
                'time_received': str(self.time_received),
                'internal_names': self.internal_names,
                'creationdate': str(self.creationdate),
                'lastmodified': str(self.lastmodified)}
