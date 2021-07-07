# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) object info update manager."""


# type annotations
from __future__ import annotations
from typing import Tuple, Union

# standard libs
import re
import logging
from datetime import datetime

# internal libs
from ...database.model import Object, ObjectType
from .interface import TNSInterface, TNSError, TNSConfig, TNSObjectSearchResult

# public interface
__all__ = ['TNSManager', ]


# initialize module level logger
log = logging.getLogger(__name__)


# NOTE: Best match for IAU names is the year followed by letters
# In 20 years this will fail. ¯\_(ツ)_/¯
IAU_PATTERN = re.compile(r'20[2-3][0-9][a-zA-Z]+')
ZTF_PATTERN = re.compile(r'ZTF.*')


class TNSManager:
    """Connect to Transient Name Server and update object info in the database."""

    tns: TNSInterface

    def __init__(self, tns: TNSInterface = None) -> None:
        """Initialize from TNS interface (or create from configuration)."""
        self.tns = tns or TNSInterface()

    @classmethod
    def from_config(cls, config: Union[dict, TNSConfig] = None) -> TNSManager:
        """Initialized manager from TNSConfig."""
        return cls(TNSInterface(config))

    def update_object(self, name: str) -> None:
        """
        Update attributes on object by `name`.

        The 'object_type.name' and 'redshift' are taken from TNS along with the IAU name.
        The object record in the database is updated with these fields and the 'data.history'
        field is appended with the previous values (if different).

        The full TNS payload is retained within `object.data.tns` less the 'photometry'.
        """
        iau_name, obj = self.__parse_object(name)
        tns_response = self.tns.search_object(iau_name)
        if tns_response.is_empty:
            raise TNSError(f'No data on object ({name}) from TNS')
        else:
            log.info(f'Found object ({name}) from TNS')
            if info := self.__build_info(iau_name, obj, tns_response):
                Object.update(obj.id, **info)

    def __parse_object(self, name: str) -> Tuple[str, Object]:
        """Determine ZTF/IAU status of `name` and fetch Object by alias."""
        if IAU_PATTERN.match(name):
            return self.__parse_iau(name)
        else:
            return self.__parse_other(name)

    @staticmethod
    def __parse_iau(name: str) -> Tuple[str, Object]:
        """Load object from IAU `name`."""
        try:
            return name, Object.from_alias(iau=name)
        except Object.NotFound as error:
            raise TNSError(str(error)) from error

    def __parse_other(self, name: str) -> Tuple[str, Object]:
        """Determine provider for `name` and query TNS for IAU name."""
        if not ZTF_PATTERN.match(name):
            name = self.__lookup_ztf(name)
        log.debug(f'Searching for IAU name ({name}) from TNS')
        iau_name = self.tns.search_name(name).objname
        if iau_name is None:
            raise TNSError(f'Could not find IAU name ({name})')
        try:
            return iau_name, Object.from_alias(ztf=name)
        except Object.NotFound as error:
            raise TNSError(str(error)) from error

    @staticmethod
    def __lookup_ztf(name: str) -> str:
        """Lookup ZTF name from database if possible."""
        log.debug(f'Searching database for ZTF name for \'{name}\'')
        try:
            obj = Object.from_name(name)
        except Object.NotFound as error:
            raise TNSError(str(error))
        if 'ztf' not in obj.aliases:
            raise TNSError(f'ZTF name unknown for \'{name}\'')
        else:
            return obj.aliases['ztf']

    def __build_info(self, iau_name: str, obj: Object, tns_response: TNSObjectSearchResult) -> dict:
        """
        Build attributes for Object.update method.
        If the new info is different, the data.history section is appended.
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
