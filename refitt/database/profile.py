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

"""User/facility profile management."""

# type annotations
from __future__ import annotations
from typing import List, Dict, Any, Optional, Union

# standard libs
import json

# internal libs
from ..core.logging import Logger
from .core.interface import execute, Interface, Table, Record, RecordNotFound
from .core import client

# external libs
from pandas import DataFrame


# initialize module level logger
log = Logger(__name__)


# table interface
user = Table('profile', 'user')
facility = Table('profile', 'facility')
facility_map = Table('profile', 'facility_map')


class UserNotFound(RecordNotFound):
    """The user profile was not found."""


class FacilityNotFound(RecordNotFound):
    """The facility profile was not found."""


_UPDATE_USER = """\
INSERT INTO "profile"."user" (user_id, user_first_name, user_last_name, user_email, user_alias, user_metadata)
VALUES (:user_id, :user_first_name, :user_last_name, :user_email, :user_alias, :user_metadata)
ON CONFLICT (user_id) DO UPDATE
    SET user_first_name = excluded.user_first_name,
        user_last_name  = excluded.user_last_name,
        user_email      = excluded.user_email,
        user_alias      = excluded.user_alias,
        user_metadata   = excluded.user_metadata;
"""


_INSERT_USER = """\
INSERT INTO "profile"."user" (user_first_name, user_last_name, user_email, user_alias, user_metadata)
VALUES (:user_first_name, :user_last_name, :user_email, :user_alias, :user_metadata)
RETURNING user_id;
"""


_REMOVE_USER = """\
DELETE FROM "profile"."user"
WHERE user_id = :user_id;
"""


class User(Record):
    """
    A user record from "profile"."user".
    """

    _fields = ('user_id', 'user_first_name', 'user_last_name', 'user_email',
               'user_alias', 'user_metadata', 'user_facilities')

    _user_id: Optional[int] = None
    _user_first_name: str = None
    _user_last_name: str = None
    _user_email: str = None
    _user_alias: str = None
    _user_metadata: Dict[str, Any] = {}
    _user_facilities: List[int] = []

    def __init__(self, **fields) -> None:
        """Extra attributes are stored under `.user_metadata`."""
        super().__init__(**{
            'user_id':         fields.pop('user_id', None),
            'user_first_name': fields.pop('user_first_name'),
            'user_last_name':  fields.pop('user_last_name'),
            'user_email':      fields.pop('user_email'),
            'user_alias':      fields.pop('user_alias'),
            'user_facilities': fields.pop('user_facilities', []),
            'user_metadata':   fields})

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @user_id.setter
    def user_id(self, value: Optional[int]) -> None:
        _user_id = None if value is None else int(value)
        if _user_id is not None and _user_id < 0:
            raise ValueError('User.user_id expects positive integer')
        else:
            self._user_id = _user_id

    @property
    def user_first_name(self) -> str:
        return self._user_first_name

    @user_first_name.setter
    def user_first_name(self, value: str) -> None:
        self._user_first_name = str(value)

    @property
    def user_last_name(self) -> str:
        return self._user_last_name

    @user_last_name.setter
    def user_last_name(self, value: str) -> None:
        self._user_last_name = str(value)

    @property
    def user_email(self) -> str:
        return self._user_email

    @user_email.setter
    def user_email(self, value: str) -> None:
        self._user_email = str(value)

    @property
    def user_alias(self) -> str:
        return self._user_alias

    @user_alias.setter
    def user_alias(self, value: str) -> None:
        self._user_alias = str(value)

    @property
    def user_facilities(self) -> List[int]:
        return self._user_facilities

    @user_facilities.setter
    def user_facilities(self, other: List[int]) -> None:
        self._user_facilities = list(map(int, other))

    @property
    def user_metadata(self) -> Dict[str, Any]:
        return self._user_metadata

    @user_metadata.setter
    def user_metadata(self, value: Union[str, Dict[str, Any]]) -> None:
        if isinstance(value, str):
            self.user_metadata = json.loads(value)  # NOTE: recursion
        elif all(isinstance(key, str) for key in dict(value)):
            self._user_metadata = dict(value)
        else:
            raise ValueError('User.user_metadata expects all keys to be str.')

    def to_dict(self, expand: bool = True) -> Dict[str, Any]:
        """
        Convert profile to dictionary.

        Options
        -------
        expand: bool (default: True)
            Expand 'user_metadata' fields.

        Returns
        -------
        profile: Dict[str, Any]
            The profile in dictionary form. The metadata fields
            are elevated for symmetry with `from_dict` if `expand` is True.
        """
        data = super().to_dict()
        if not expand:
            return data
        else:
            metadata = data.pop('user_metadata')
            return {**data, **metadata}

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> User:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            with client.connect().begin() as transaction:
                profile = super()._from_unique(table, field, value, transaction)
                profile.user_metadata = profile.user_metadata.pop('user_metadata')
                profile.user_facilities = cls.get_facilities(profile.user_id, transaction)  # noqa (return type)
                return profile  # noqa (return type)
        except RecordNotFound as error:
            raise UserNotFound(*error.args) from error

    @classmethod
    def from_id(cls, user_id: int) -> User:
        """Load user from `user_id`."""
        return cls._from_unique(user, 'user_id', user_id)

    @classmethod
    def from_email(cls, user_email: str) -> User:
        """Load user from `user_email`."""
        return cls._from_unique(user, 'user_email', user_email)

    @classmethod
    def from_alias(cls, user_alias: str) -> User:
        """Load user from `user_alias`."""
        return cls._from_unique(user, 'user_alias', user_alias)

    _FACTORIES = {'user_id': 'from_id', 'user_email': 'from_email',
                  'user_alias': 'from_alias'}

    @classmethod
    def from_id_or_alias(cls, value: str) -> User:
        """
        Smart factory guess whether to use from_id or from_alias based
        on the `value`.
        """
        try:
            user_id = int(value)
            user_alias = None
        except ValueError:
            user_id = None
            user_alias = value
        if user_id:
            return cls.from_id(user_id)
        else:
            return cls.from_alias(user_alias)

    def to_database(self) -> int:
        """Add user profile into database."""
        data = self.to_dict(expand=False)
        data['user_metadata'] = json.dumps(data['user_metadata'])
        user_id = data.pop('user_id')
        user_facilities = data.pop('user_facilities')
        with client.connect().begin() as transaction:
            if user_id:
                execute(_UPDATE_USER, interface=transaction, user_id=user_id, **data)
                self.remove_facilities(user_id, transaction)
                self.add_facilities(user_id, user_facilities, transaction)
                log.info(f'updated user profile: user_id={user_id}')
            else:
                ((user_id, ),) = execute(_INSERT_USER, interface=transaction, **data)
                self.add_facilities(user_id, user_facilities, transaction)
                log.info(f'added user profile: user_id={user_id}')
            return user_id

    @staticmethod
    def get_facilities(user_id: int, interface: Optional[Interface] = None) -> List[int]:
        """Get list of facility_id's for `user_id` from "profile"."facility_map"."""
        records = facility_map.select(['facility_id'], where=[f'user_id = {user_id}'],
                                      interface=interface, limit=None)
        return records.loc[:, 'facility_id'].to_list()

    @staticmethod
    def add_facilities(user_id: int, facility_ids: List[int], interface: Optional[Interface] = None) -> None:
        """Insert all `facility_ids` with `user_id` into "user"."facility_map"."""
        records = DataFrame({'facility_id': list(facility_ids)}).assign(user_id=user_id)
        facility_map.insert(records, interface=interface)
        log.info(f'updated facility_map: user_id={user_id}, facility_id={facility_ids}')

    @staticmethod
    def remove_facilities(user_id: int, interface: Optional[Interface] = None) -> None:
        """Remove all records from "user"."facility_map" for `user_id`."""
        execute('DELETE FROM "profile"."facility_map" WHERE user_id = :user_id',
                interface=interface, user_id=user_id)
        log.info(f'removed facility_map records for user_id={user_id}')

    @classmethod
    def remove(cls, user_id: int) -> None:
        """Remove user profile from database."""
        profile = cls.from_id(user_id)
        with client.connect().begin() as transaction:
            profile.remove_facilities(profile.user_id, transaction)  # foreign key constraint
            execute('DELETE FROM "profile"."user" WHERE user_id = :user_id',
                    interface=transaction, user_id=profile.user_id)
            log.info(f'removed user profile for user_id={profile.user_id}')


_UPDATE_FACILITY = """\
INSERT INTO "profile"."facility" (facility_id, facility_name, facility_latitude, facility_longitude,
                                  facility_altitude, facility_limiting_magnitude, facility_metadata)
VALUES (:facility_id, :facility_name, :facility_latitude, :facility_longitude, :facility_altitude,
        :facility_limiting_magnitude, :facility_metadata)
ON CONFLICT (facility_id) DO UPDATE
    SET facility_name = excluded.facility_name,
        facility_latitude = excluded.facility_latitude,
        facility_longitude = excluded.facility_longitude,
        facility_altitude = excluded.facility_altitude,
        facility_limiting_magnitude = excluded.facility_limiting_magnitude,
        facility_metadata = excluded.facility_metadata;
"""


_INSERT_FACILITY = """\
INSERT INTO "profile"."facility" (facility_name, facility_latitude, facility_longitude, facility_altitude,
                                  facility_limiting_magnitude, facility_metadata)
VALUES (:facility_name, :facility_latitude, :facility_longitude, :facility_altitude,
        :facility_limiting_magnitude, :facility_metadata)
RETURNING facility_id;
"""


class Facility(Record):
    """
    A record from "profile"."facility".
    """

    _fields = ('facility_id', 'facility_name',
               'facility_latitude', 'facility_longitude', 'facility_altitude',
               'facility_limiting_magnitude', 'facility_users', 'facility_metadata')

    _facility_id: Optional[int] = None
    _facility_name: str = None
    _facility_latitude: float = None
    _facility_longitude: float = None
    _facility_altitude: float = None
    _facility_limiting_magnitude: float = None
    _facility_metadata: Dict[str, Any] = {}
    _facility_users: List[int] = []

    _FACTORIES = {'facility_id': 'from_id', 'facility_name': 'from_name'}

    def __init__(self, **fields) -> None:
        """Extra attributes are stored under `.facility_metadata`."""
        super().__init__(**{
            'facility_id':         fields.pop('facility_id', None),
            'facility_name':       fields.pop('facility_name'),
            'facility_latitude':   fields.pop('facility_latitude'),
            'facility_longitude':  fields.pop('facility_longitude'),
            'facility_altitude':   fields.pop('facility_altitude'),
            'facility_limiting_magnitude': fields.pop('facility_limiting_magnitude'),
            'facility_users': fields.pop('facility_users', []),
            'facility_metadata':   fields})

    @property
    def facility_id(self) -> int:
        return self._facility_id

    @facility_id.setter
    def facility_id(self, value: Optional[int]) -> None:
        self._facility_id = None if value is None else int(value)

    @property
    def facility_name(self) -> str:
        return self._facility_name

    @facility_name.setter
    def facility_name(self, value: str) -> None:
        self._facility_name = str(value)

    @property
    def facility_latitude(self) -> float:
        return self._facility_latitude

    @facility_latitude.setter
    def facility_latitude(self, value: float) -> None:
        self._facility_latitude = float(value)

    @property
    def facility_longitude(self) -> float:
        return self._facility_longitude

    @facility_longitude.setter
    def facility_longitude(self, value: float) -> None:
        self._facility_longitude = float(value)

    @property
    def facility_altitude(self) -> float:
        return self._facility_altitude

    @facility_altitude.setter
    def facility_altitude(self, value: float) -> None:
        self._facility_altitude = float(value)

    @property
    def facility_limiting_magnitude(self) -> float:
        return self._facility_limiting_magnitude

    @facility_limiting_magnitude.setter
    def facility_limiting_magnitude(self, value: float) -> None:
        self._facility_limiting_magnitude = float(value)

    @property
    def facility_users(self) -> List[int]:
        return self._facility_users

    @facility_users.setter
    def facility_users(self, other: List[int]) -> None:
        self._facility_users = list(map(int, other))

    @property
    def facility_metadata(self) -> Dict[str, Any]:
        return self._facility_metadata

    @facility_metadata.setter
    def facility_metadata(self, value: Union[str, Dict[str, Any]]) -> None:
        if isinstance(value, str):
            self.facility_metadata = json.loads(value)  # NOTE: recursion
        elif all(isinstance(key, str) for key in dict(value)):
            self._facility_metadata = dict(value)
        else:
            raise ValueError(f'{self.__class__.__name__}.facility_metadata requires all keys to be str.')

    def to_dict(self, expand: bool = True) -> Dict[str, Any]:
        """
        Convert profile to dictionary.

        Options
        -------
        expand: bool (default: True)
            Expand 'facility_metadata' fields.

        Returns
        -------
        profile: Dict[str, Any]
            The profile in dictionary form. The metadata fields
            are elevated for symmetry with `from_dict` if `expand` is True.
        """
        data = super().to_dict()
        if not expand:
            return data
        else:
            metadata = data.pop('facility_metadata')
            return {**data, **metadata}

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Facility:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            with client.connect().begin() as transaction:
                profile = super()._from_unique(table, field, value, transaction)
                profile.facility_metadata = profile.facility_metadata.pop('facility_metadata')
                profile.facility_users = cls.get_users(profile.facility_id, transaction)  # noqa (return type)
                return profile  # noqa (return type)
        except RecordNotFound as error:
            raise FacilityNotFound(*error.args) from error

    @classmethod
    def from_id(cls, facility_id: int) -> Facility:
        """Load facility from `facility_id`."""
        return cls._from_unique(facility, 'facility_id', facility_id)

    @classmethod
    def from_name(cls, facility_name: str) -> Facility:
        """Load facility from `facility_name`."""
        return cls._from_unique(facility, 'facility_name', facility_name)

    @classmethod
    def from_id_or_name(cls, value: str) -> Facility:
        """
        Smart factory guess whether to use from_id or from_name based
        on the `value`.
        """
        try:
            facility_id = int(value)
            facility_name = None
        except ValueError:
            facility_id = None
            facility_name = value
        if facility_id:
            return cls.from_id(facility_id)
        else:
            return cls.from_name(facility_name)

    def to_database(self) -> int:
        """Insert facility profile into database."""
        data = self.to_dict(expand=False)
        data['facility_metadata'] = json.dumps(data['facility_metadata'])
        facility_id = data.pop('facility_id')
        facility_users = data.pop('facility_users')
        with client.connect().begin() as transaction:
            if facility_id:
                execute(_UPDATE_FACILITY, interface=transaction, facility_id=facility_id, **data)
                self.remove_users(facility_id, transaction)
                self.add_users(facility_id, facility_users, transaction)
                log.info(f'updated facility profile: facility_id={facility_id}')
            else:
                ((facility_id, ),) = execute(_INSERT_FACILITY, interface=transaction, **data)
                self.add_users(facility_id, facility_users, transaction)
                log.info(f'added facility profile: facility_id={facility_id}')
            return facility_id

    @staticmethod
    def get_users(facility_id: int, interface: Interface = None) -> List[int]:
        """Select all "user_id"s associated with `facility_id` from "profile"."facility_map"."""
        records = facility_map.select(['user_id'], where=[f'facility_id = {facility_id}'],
                                      interface=interface, limit=None)
        return records.loc[:, 'user_id'].to_list()

    @staticmethod
    def add_users(facility_id: int, user_ids: List[int], interface: Optional[Interface] = None) -> None:
        """Insert all `user_ids` with `facility_id` into "profile"."facility_map"."""
        records = DataFrame({'user_id': list(user_ids)}).assign(facility_id=facility_id)
        facility_map.insert(records, interface=interface)
        log.info(f'updated facility_map: facility_id={facility_id}, user_id={user_ids}')

    @staticmethod
    def remove_users(facility_id: int, interface: Optional[Interface] = None) -> None:
        """Remove all records from "profile"."facility_map" for `facility_id`."""
        execute('DELETE FROM "profile"."facility_map" WHERE facility_id = :facility_id',
                interface=interface, facility_id=facility_id)
        log.info(f'removed facility_map records for facility_id={facility_id}')

    @classmethod
    def remove(cls, facility_id: int) -> None:
        """Remove facility profile from database."""
        profile = cls.from_id(facility_id)
        with client.connect().begin() as transaction:
            profile.remove_users(profile.facility_id, transaction)  # foreign key constraint
            execute('DELETE FROM "profile"."facility" WHERE facility_id = :facility_id',
                    interface=transaction, facility_id=profile.facility_id)
            log.info(f'removed facility profile for facility_id={profile.facility_id}')
