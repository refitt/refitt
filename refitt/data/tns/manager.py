# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) object info update manager."""


# type annotations
from __future__ import annotations
from typing import Tuple, Union, Dict

# standard libs
import re
import logging
from datetime import datetime
from abc import ABC, abstractmethod

# internal libs
from ...database.model import Object, ObjectType
from .interface import TNSInterface, TNSError, TNSConfig, TNSObjectSearchResult
from .catalog import TNSCatalog, TNSRecord

# public interface
__all__ = ['TNSManager', 'TNSQueryManager', 'TNSCatalogManager', ]


# initialize module level logger
log = logging.getLogger(__name__)


class TNSManager(ABC):
    """Generic interface for managing the TNSInterface to update objects in the database."""

    tns: TNSInterface

    def __init__(self, tns: TNSInterface = None) -> None:
        """Initialize from existing TNSInterface (or create from configuration)."""
        self.tns = tns or TNSInterface()

    @classmethod
    def from_config(cls, config: Union[dict, TNSConfig] = None) -> TNSManager:
        """Initialized manager from TNSConfig."""
        return cls(TNSInterface(config))

    @abstractmethod
    def update_object(self, name: str) -> None:
        """
        Update attributes on object by `name`.

        The `name` can be any recognizable designation (e.g., IAU, ZTF, Antares).

        The object 'type' and 'redshift' are taken from TNS along with other 'internal_names'.
        The object record in the database is updated with these fields and 'data.history'
        is appended with the previous values (if different).

        The full TNS payload is retained within `object.data.tns` less the 'photometry'.
        """


# NOTE: Best match for IAU names is the year followed by letters
# In 20 years this will fail. ¯\_(ツ)_/¯
IAU_PATTERN = re.compile(r'20[2-3][0-9][a-zA-Z]+')
ZTF_PATTERN = re.compile(r'ZTF.*')


class TNSQueryManager(TNSManager):
    """Connect to Transient Name Server and update object info in the database."""

    tns: TNSInterface

    def update_object(self, name: str) -> None:
        """
        Information gathered by querying the live TNS service.
        First for the IAU name if not given explicitly, and then for the data.
        """
        try:
            object = Object.from_name(name)
        except Object.NotFound as error:
            log.warning(f'Cannot add new objects using TNSQueryManager')
            raise TNSError(str(error)) from error
        if 'iau' in object.aliases:
            if name != object.aliases['iau']:
                log.debug(f'Searching with name {object.aliases["iau"]} <- {name}')
                name = object.aliases['iau']
        elif 'ztf' in object.aliases:
            log.debug(f'Searching TNS for IAU name {name}')
            name = self.tns.search_name(name).objname
            if name is None:
                raise TNSError(f'Could not find IAU name {name}')
        else:
            raise TNSError(f'No support identifier found {name}')
        response = self.tns.search_object(name)
        if response.is_empty:
            raise TNSError(f'No data on object {name}')
        else:
            if info := self.__build_info(name, object, response):
                Object.update(object.id, **info)
            else:
                log.info(f'No changes for {name}')

    def __build_info(self, iau_name: str, obj: Object, tns_response: TNSObjectSearchResult) -> dict:
        """
        Build attributes for `Object.update` method.
        If the new info is different, the `data.history` section is appended.
        """
        type_id = self.__get_type_id(tns_response)
        redshift = tns_response.redshift
        type_changed = type_id != obj.type_id
        redshift_changed = redshift != obj.redshift
        iau_name_changed = 'iau' not in obj.aliases
        tns_data_changed = obj.data.get('tns', {}) != tns_response.data
        if type_changed or redshift_changed:  # keep history of previous values
            return {
                'type_id': type_id, 'redshift': redshift, 'aliases': {**obj.aliases, 'iau': iau_name},
                'data': {**obj.data, 'history': self.__build_history(obj), 'tns': tns_response.data}
            }
        elif iau_name_changed or tns_data_changed:
            return {
                'aliases': {**obj.aliases, 'iau': iau_name},
                'data': {**obj.data, 'tns': tns_response.data}
            }
        else:
            return {}

    def __build_history(self, obj: Object) -> dict:
        """Build 'history' data dictionary."""
        previous_history = obj.data.get('history', {})
        return {**previous_history, self.__get_timestamp(): {'type_id': obj.type_id, 'redshift': obj.redshift}}

    @staticmethod
    def __get_type_id(tns_response: TNSObjectSearchResult) -> int:
        """Get or create the `ObjectType` given `tns_response`."""
        type_name = tns_response.object_type_name or 'Unknown'
        object_type = ObjectType.get_or_create(type_name)
        return object_type.id

    @staticmethod
    def __get_timestamp() -> str:
        """The current timestamp in ISO format."""
        return str(datetime.now().astimezone())


class TNSCatalogManager(TNSManager):
    """Load TNSCatalog and update object info in the database."""

    __catalog: TNSCatalog = None

    def update_object(self, name: str) -> None:
        """Look up object by `name` and update database with info from TNSCatalog."""
        try:
            object = Object.from_name(name)
        except Object.NotFound:
            record = self.catalog.get(name)  # must be name pattern recognized by catalog
            log.info(f'Creating new object for {name}')
            Object.add({'type_id': self.__get_type_id(record), 'aliases': self.__get_names(record),
                        'ra': record.ra, 'dec': record.declination, 'redshift': record.redshift,
                        'data': {'tns': record.to_json()}})
        else:
            # find best alternate identifier for catalog search
            for provider in ('iau', 'ztf', 'atlas'):  # preferred ordering
                if provider in object.aliases:
                    if name != object.aliases[provider]:
                        log.debug(f'Searching with name \'{object.aliases[provider]} <- {name}\'')
                        name = object.aliases[provider]
                    break
            else:
                raise TNSError(f'Object ({name}) not found in catalog')
            record = self.catalog.get(name)
            self.__ensure_iau_pattern(record.name)
            if info := self.__build_info(object, record):
                Object.update(object.id, **info)
            else:
                log.info(f'No changes found for {name}')

    @property
    def catalog(self) -> TNSCatalog:
        """Access TNSCatalog, regularly updated when necessary."""
        if not self.__catalog:
            self.__catalog = TNSCatalog.from_web(cache=True)
            return self.__catalog
        else:
            self.__catalog.refresh()
            return self.__catalog

    def __build_history(self, obj: Object) -> dict:
        """Build 'history' data dictionary."""
        previous_history = obj.data.get('history', {})
        return {**previous_history, self.__get_timestamp(): {'type_id': obj.type_id, 'redshift': obj.redshift}}

    @staticmethod
    def __get_type_id(record: TNSRecord) -> int:
        """Get or create the `ObjectType` given `record`."""
        return ObjectType.get_or_create(record.type or 'Unknown').id

    @staticmethod
    def __get_timestamp() -> str:
        """The current timestamp in ISO format."""
        return str(datetime.now().astimezone())

    def __build_info(self, obj: Object, record: TNSRecord) -> dict:
        """
        Build attributes for `Object.update` method.
        If the new info is different, the `data.history` section is appended.
        """
        type_id = self.__get_type_id(record)
        redshift = record.redshift
        type_changed = type_id != obj.type_id
        redshift_changed = redshift != obj.redshift
        if type_changed or redshift_changed:  # keep history of previous values
            return {
                'type_id': type_id, 'redshift': redshift, 'aliases': {**obj.aliases, 'iau': record.name},
                'data': {**obj.data, 'history': self.__build_history(obj), 'tns': record.to_json()}
            }
        elif 'iau' not in obj.aliases:
            return {
                'aliases': {**obj.aliases, 'iau': record.name},
                'data': {**obj.data, 'tns': record.to_json()}
            }
        else:
            return {}

    @staticmethod
    def __ensure_iau_pattern(name: str) -> None:
        """Raises TNSError if `name` does not match IAU format."""
        if not Object.name_patterns['iau'].match(name):
            raise TNSError(f'Name \'{name}\' does not match IAU pattern')

    @staticmethod
    def __get_names(record: TNSRecord) -> Dict[str, str]:
        """Format `Object.aliases` dictionary from TNSRecord."""
        aliases = {'iau': record.name}
        internal_names = record.internal_names.split(',')
        for provider, pattern in Object.name_patterns.items():
            for name in internal_names:
                if pattern.match(name):
                    aliases[provider] = name
        return aliases
