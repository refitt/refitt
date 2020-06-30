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

"""Observational data as represented in the REFITT database."""

# type annotations
from __future__ import annotations
from typing import Dict, TypeVar, Optional, Union, Any

# standard libs
import re
import json
import string
import random
import hashlib
import functools
from datetime import datetime, timedelta

# external libs
from pandas import Timestamp

# internal libs
from ..core.config import config, ConfigurationError
from ..core.logging import Logger
from .core.interface import execute, Interface, Table, Record, RecordNotFound
from .core import client


# initialize module level logger
log = Logger(__name__)


# interface
object_type      = Table('observation', 'object_type')
object           = Table('observation', 'object')  # noqa (shadows builtin name "object")
source_type      = Table('observation', 'source_type')
source           = Table('observation', 'source')
observation_type = Table('observation', 'observation_type')
observation      = Table('observation', 'observation')
alert            = Table('observation', 'alert')
file             = Table('observation', 'file')


class ObjectTypeNotFound(RecordNotFound):
    """The object_type was not found in the database."""


_UPDATE_OBJECT_TYPE = """\
INSERT INTO "observation"."object_type" (object_type_id, object_type_name, object_type_description)
VALUES (:object_type_id, :object_type_name, :object_type_description)
ON CONFLICT (object_type_id) DO UPDATE
    SET object_type_name        = excluded.object_type_name,
        object_type_description = excluded.object_type_description;
"""


_INSERT_OBJECT_TYPE = """\
INSERT INTO "observation"."object_type" (object_type_name, object_type_description)
VALUES (:object_type_name, :object_type_description)
RETURNING object_type_id;
"""


_REMOVE_OBJECT_TYPE = """\
DELETE FROM "observation"."object_type"
WHERE object_type_id = :object_type_id;
"""


class ObjectType(Record):
    """
    A record from the "observation"."object_type" table.

    Example
    -------
    >>> from refitt.database.observation import ObjectType
    >>> ObjectType.from_database(object_type_name='SNIa')
    ObjectType(object_type_id=2, object_type_name='SNIa',
               object_type_description='WD detonation, Type Ia SN')
    """

    _fields = ('object_type_id', 'object_type_name', 'object_type_description')
    _masked = False

    _object_type_id: Optional[int] = None
    _object_type_name: str = None
    _object_type_description: str = None

    _FACTORIES = {'object_type_id': 'from_id',
                  'object_type_name': 'from_name', }

    @property
    def object_type_id(self) -> Optional[int]:
        return self._object_type_id

    @object_type_id.setter
    def object_type_id(self, value: int) -> None:
        _object_type_id = None if value is None else int(value)
        if _object_type_id is not None and _object_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.object_type_id expects positive integer')
        else:
            self._object_type_id = _object_type_id

    @property
    def object_type_name(self) -> str:
        return self._object_type_name

    @object_type_name.setter
    def object_type_name(self, value: str) -> None:
        self._object_type_name = str(value)

    @property
    def object_type_description(self) -> str:
        return self._object_type_description

    @object_type_description.setter
    def object_type_description(self, value: str) -> None:
        self._object_type_description = str(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> ObjectType:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise ObjectTypeNotFound(*error.args) from error

    @classmethod
    def from_id(cls, object_type_id: int, interface: Interface = None) -> ObjectType:
        """Get object_type record from `object_type_id`."""
        return cls._from_unique(object_type, 'object_type_id', object_type_id, interface)

    @classmethod
    def from_name(cls, object_type_name: int, interface: Interface = None) -> ObjectType:
        """Get object_type record from `object_type_name`."""
        return cls._from_unique(object_type, 'object_type_name', object_type_name, interface)

    def to_database(self) -> int:
        """Add object_type record to the database."""
        data = self.to_dict()
        object_type_id = data.pop('object_type_id')
        if object_type_id:
            execute(_UPDATE_OBJECT_TYPE, object_type_id=object_type_id, **data)
            log.info(f'updated object_type: object_type_id={object_type_id}')
        else:
            ((object_type_id, ),) = execute(_INSERT_OBJECT_TYPE, **data)
            log.info(f'added object_type: object_type_id={object_type_id}')
        return object_type_id

    @classmethod
    def remove(cls, object_type_id: int) -> None:
        """Purge the object_type record for `object_type_id`."""
        execute(_REMOVE_OBJECT_TYPE, object_type_id=object_type_id)


class ObjectNotFound(RecordNotFound):
    """The object was not found in the database."""


_UPDATE_OBJECT = """\
INSERT INTO "observation"."object" (object_id, object_type_id, object_name, object_aliases,
                                    object_ra, object_dec, object_redshift, object_metadata)
VALUES (:object_id, :object_type_id, :object_name, :object_aliases, :object_ra, :object_dec,
        :object_redshift, :object_metadata)
ON CONFLICT (object_id) DO UPDATE
    SET object_type_id        = excluded.object_type_id,
        object_name           = excluded.object_name,
        object_aliases        = excluded.object_aliases,
        object_ra             = excluded.object_ra,
        object_dec            = excluded.object_dec,
        object_redshift       = excluded.object_redshift,
        object_metadata       = excluded.object_metadata;
"""


_INSERT_OBJECT = """\
INSERT INTO "observation"."object" (object_type_id, object_name, object_aliases,
                                    object_ra, object_dec, object_redshift, object_metadata)
VALUES (:object_type_id, :object_name, :object_aliases, :object_ra, :object_dec,
        :object_redshift, :object_metadata)
RETURNING object_id;
"""


_REMOVE_OBJECT = """\
DELETE FROM "observation"."object"
WHERE object_id = :object_id;
"""


_SELECT_OBJECT_BY_ALIAS = """\
SELECT object_id, object_type_id, object_name, object_aliases,
       object_ra, object_dec, object_redshift, object_metadata
FROM "observation"."object"
WHERE object_aliases @> :json
"""


_CHECK_OBJECT_BY_ALIAS = """\
SELECT object_id
FROM "observation"."object"
WHERE object_aliases @> :json
LIMIT 1
"""


class Object(Record):
    """
    A record from the "observation"."object" table.

    Example
    -------
    >>> from refitt.database.observation import Object
    >>> Object.from_alias(antares=123)
    Object(object_id=123, object_type_id=2, object_name='antares::123',
           object_aliases={'antares': 123}, object_ra=42.1, object_dec=3.14,
           object_redshift=0.1, object_metadata={})
    """

    _fields = ('object_id', 'object_type_id', 'object_name', 'object_aliases',
               'object_ra', 'object_dec', 'object_redshift', 'object_metadata')
    _masked = False

    _object_id: Optional[int] = None
    _object_type_id: int = None
    _object_name: str = None
    _object_aliases: Dict[str, int] = {}
    _object_ra: float = None
    _object_dec: float = None
    _object_redshift: float = None
    _object_metadata: Dict[str, Any] = {}

    _FACTORIES = {'object_id': 'from_id', }

    @property
    def object_id(self) -> Optional[int]:
        return self._object_id

    @object_id.setter
    def object_id(self, value: int) -> None:
        _object_id = None if value is None else int(value)
        if _object_id is not None and _object_id < 0:
            raise ValueError(f'{self.__class__.__name__}.object_id expects positive integer')
        else:
            self._object_id = _object_id

    @property
    def object_type_id(self) -> int:
        return self._object_type_id

    @object_type_id.setter
    def object_type_id(self, value: int) -> None:
        _object_type_id = int(value)
        if _object_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.object_type_id expects positive integer')
        else:
            self._object_type_id = _object_type_id

    @property
    def object_name(self) -> str:
        return self._object_name

    @object_name.setter
    def object_name(self, value: str) -> None:
        self._object_name = str(value)

    @property
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return self._object_aliases

    @object_aliases.setter
    def object_aliases(self, value: Dict[str, Union[int, str]]) -> None:
        self._object_aliases = dict(value)

    @property
    def object_ra(self) -> float:
        return self._object_ra

    @object_ra.setter
    def object_ra(self, value: float) -> None:
        self._object_ra = float(value)

    @property
    def object_dec(self) -> float:
        return self._object_dec

    @object_dec.setter
    def object_dec(self, value: float) -> None:
        self._object_dec = float(value)

    @property
    def object_redshift(self) -> float:
        return self._object_redshift

    @object_redshift.setter
    def object_redshift(self, value: float) -> None:
        self._object_redshift = float(value)

    @property
    def object_metadata(self) -> Dict[str, Any]:
        return self._object_metadata

    @object_metadata.setter
    def object_metadata(self, value: Dict[str, Any]) -> None:
        self._object_metadata = dict(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Object:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise ObjectNotFound(*error.args) from error

    @classmethod
    def from_id(cls, object_id: int, interface: Interface = None) -> Object:
        """Get object record from `object_id`."""
        return cls._from_unique(object, 'object_id', object_id, interface)

    @classmethod
    def from_alias(cls, interface: Interface = None, **key) -> Object:
        """Get object record from `object_type_name`."""
        if len(key) != 1:
            raise AttributeError(f'Object.from_alias expects precisely one named field.')
        ((key_, value_), ) = key.items()
        if not isinstance(value_, (int, str)):
            raise TypeError('Object.from_alias expects str or int for the value.')
        records = execute(_SELECT_OBJECT_BY_ALIAS, interface=interface,
                          json=json.dumps(key)).fetchall()
        if not records:
            raise ObjectNotFound(f'alias {key_}={value_}')
        (record, ) = records
        return cls.from_dict(dict(zip(cls._fields, record)))

    def to_database(self) -> int:
        """Add object record to the database."""
        data = self.to_dict()
        data['object_aliases'] = json.dumps(data['object_aliases'])
        data['object_metadata'] = json.dumps(data['object_metadata'])
        object_id = data.pop('object_id')
        if object_id:
            # if you declared the object_id, just overwrite it
            execute(_UPDATE_OBJECT, object_id=object_id, **data)
            log.info(f'updated object: object_id={object_id}')
        else:
            # check if pre-existing objects share any aliases
            with client.connect().begin() as transaction:
                old = {}
                for name, value in self.object_aliases.items():
                    try:
                        other = Object.from_alias(**{name: value}, interface=transaction)
                        old[other.object_id] = other
                        if len(old) > 1:
                            log.warning(f'duplicate objects found for alias: {name}={value}')
                    except ObjectNotFound:
                        pass
                if len(old) == 0:
                    # no pre-existing objects exist for these aliases
                    # create a new object record
                    ((object_id, ),) = execute(_INSERT_OBJECT, **data)
                    log.info(f'added object: object_id={object_id}')
                else:
                    # merge prior aliases with current aliases and update object record
                    object_id, *_ = old.keys()
                    old = old[object_id]
                    data['object_aliases'] = json.dumps({**old.object_aliases, **self.object_aliases})
                    execute(_UPDATE_OBJECT, object_id=object_id, **data)
                    log.info(f'updated object: object_id={object_id}')
        return object_id

    @classmethod
    def remove(cls, object_id: int) -> None:
        """Purge the object record for `object_id`."""
        execute(_REMOVE_OBJECT, object_id=object_id)


class SourceTypeNotFound(RecordNotFound):
    """The source_type was not found in the database."""


_UPDATE_SOURCE_TYPE = """\
INSERT INTO "observation"."source_type" (source_type_id, source_type_name, source_type_description)
VALUES (:source_type_id, :source_type_name, :source_type_description)
ON CONFLICT (source_type_id) DO UPDATE
    SET source_type_name        = excluded.source_type_name,
        source_type_description = excluded.source_type_description;
"""


_INSERT_SOURCE_TYPE = """\
INSERT INTO "observation"."source_type" (source_type_name, source_type_description)
VALUES (:source_type_name, :source_type_description)
RETURNING source_type_id;
"""


_REMOVE_SOURCE_TYPE = """\
DELETE FROM "observation"."source_type"
WHERE source_type_id = :source_type_id;
"""


class SourceType(Record):
    """
    A record from the "observation"."source_type" table.

    Example
    -------
    >>> from refitt.database.observation import SourceType
    >>> SourceType.from_name('broker')
    SourceType(source_type_id=3, source_type_name='broker',
               source_type_description='Alerts from LSST (or other) data brokers.')
    """

    _fields = ('source_type_id', 'source_type_name', 'source_type_description')
    _masked = False

    _source_type_id: Optional[int] = None
    _source_type_name: str = None
    _source_type_description: str = None

    _FACTORIES = {'source_type_id': 'from_id', 'source_type_name': 'from_name', }

    @property
    def source_type_id(self) -> Optional[int]:
        return self._source_type_id

    @source_type_id.setter
    def source_type_id(self, value: int) -> None:
        _source_type_id = None if value is None else int(value)
        if _source_type_id is not None and _source_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.source_type_id expects positive integer')
        else:
            self._source_type_id = _source_type_id

    @property
    def source_type_name(self) -> str:
        return self._source_type_name

    @source_type_name.setter
    def source_type_name(self, value: str) -> None:
        self._source_type_name = str(value)

    @property
    def source_type_description(self) -> str:
        return self._source_type_description

    @source_type_description.setter
    def source_type_description(self, value: str) -> None:
        self._source_type_description = str(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> SourceType:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise SourceTypeNotFound(*error.args) from error

    @classmethod
    def from_id(cls, source_type_id: int, interface: Interface = None) -> SourceType:
        """Get source_type record from `source_type_id`."""
        return cls._from_unique(source_type, 'source_type_id', source_type_id, interface)

    @classmethod
    def from_name(cls, source_type_name: int, interface: Interface = None) -> SourceType:
        """Get source_type record from `source_type_name`."""
        return cls._from_unique(source_type, 'source_type_name', source_type_name, interface)

    def to_database(self) -> int:
        """Add source_type record to the database."""
        data = self.to_dict()
        source_type_id = data.pop('source_type_id')
        if source_type_id:
            execute(_UPDATE_SOURCE_TYPE, source_type_id=source_type_id, **data)
            log.info(f'updated source_type: source_type_id={source_type_id}')
        else:
            ((source_type_id, ),) = execute(_INSERT_SOURCE_TYPE, **data)
            log.info(f'added source_type: source_type_id={source_type_id}')
        return source_type_id

    @classmethod
    def remove(cls, source_type_id: int) -> None:
        """Purge the source_type record for `source_type_id`."""
        execute(_REMOVE_SOURCE_TYPE, source_type_id=source_type_id)


class SourceNotFound(RecordNotFound):
    """The source was not found in the database."""


_UPDATE_SOURCE = """\
INSERT INTO "observation"."source" (source_id, source_type_id, facility_id, user_id, source_name,
                                    source_description, source_metadata)
VALUES (:source_id, :source_type_id, :facility_id, :user_id, :source_name,
        :source_description, :source_metadata)
ON CONFLICT (source_id) DO UPDATE
    SET source_type_id     = excluded.source_type_id,
        facility_id        = excluded.facility_id,
        user_id            = excluded.user_id,
        source_name        = excluded.source_name,
        source_description = excluded.source_description,
        source_metadata    = excluded.source_metadata;
"""


_INSERT_SOURCE = """\
INSERT INTO "observation"."source" (source_type_id, facility_id, user_id, source_name,
                                    source_description, source_metadata)
VALUES (:source_type_id, :facility_id, :user_id, :source_name,
        :source_description, :source_metadata)
RETURNING source_id;
"""


_REMOVE_SOURCE = """\
DELETE FROM "observation"."source"
WHERE source_id = :source_id;
"""


class Source(Record):
    """
    A record from the "observation"."source" table.

    Example
    -------
    >>> from refitt.database.observation import Source
    >>> Source.from_name('antares')
    Source(source_id=4, source_type_id=3, facility_id=None, user_id=None, source_name='antares',
           source_description='ANTARES is an Alert Broker developed by the NOAO for ZTF and LSST.',
           source_metadata={})
    """

    _fields = ('source_id', 'source_type_id', 'facility_id', 'user_id', 'source_name',
               'source_description', 'source_metadata')
    _masked = False

    _source_id: Optional[int] = None
    _source_type_id: int = None
    _facility_id: Optional[int] = None
    _user_id: Optional[int] = None
    _source_name: str = None
    _source_description: str = None
    _source_metadata: Dict[str, Any] = {}

    _FACTORIES = {'source_id': 'from_id', 'source_name': 'from_name', }

    @property
    def source_id(self) -> Optional[int]:
        return self._source_id

    @source_id.setter
    def source_id(self, value: int) -> None:
        _source_id = None if value is None else int(value)
        if _source_id is not None and _source_id < 0:
            raise ValueError(f'{self.__class__.__name__}.source_id expects positive integer')
        else:
            self._source_id = _source_id

    @property
    def source_type_id(self) -> int:
        return self._source_type_id

    @source_type_id.setter
    def source_type_id(self, value: int) -> None:
        _source_type_id = int(value)
        if _source_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.source_type_id expects positive integer')
        else:
            self._source_type_id = _source_type_id

    @property
    def facility_id(self) -> Optional[int]:
        return self._facility_id

    @facility_id.setter
    def facility_id(self, value: int) -> None:
        _facility_id = None if value is None else int(value)
        if _facility_id is not None and _facility_id < 0:
            raise ValueError(f'{self.__class__.__name__}.facility_id expects positive integer')
        else:
            self._facility_id = _facility_id

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        _user_id = None if value is None else int(value)
        if _user_id is not None and _user_id < 0:
            raise ValueError(f'{self.__class__.__name__}.user_id expects positive integer')
        else:
            self._user_id = _user_id

    @property
    def source_name(self) -> str:
        return self._source_name

    @source_name.setter
    def source_name(self, value: str) -> None:
        self._source_name = str(value)

    @property
    def source_description(self) -> str:
        return self._source_description

    @source_description.setter
    def source_description(self, value: str) -> None:
        self._source_description = str(value)

    @property
    def source_metadata(self) -> Dict[str, Any]:
        return self._source_metadata

    @source_metadata.setter
    def source_metadata(self, value: Dict[str, Any]) -> None:
        self._source_metadata = dict(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Source:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise SourceNotFound(*error.args) from error

    @classmethod
    def from_id(cls, source_id: int, interface: Interface = None) -> Source:
        """Get source record from `source_id`."""
        return cls._from_unique(source, 'source_id', source_id, interface)

    @classmethod
    def from_name(cls, source_name: int, interface: Interface = None) -> Source:
        """Get source record from `source_name`."""
        return cls._from_unique(source, 'source_name', source_name, interface)

    def to_database(self) -> int:
        """Add source record to the database."""
        data = self.to_dict()
        data['source_metadata'] = json.dumps(data['source_metadata'])
        source_id = data.pop('source_id')
        if source_id:
            execute(_UPDATE_SOURCE, source_id=source_id, **data)
            log.info(f'updated source: source_id={source_id}')
        else:
            ((source_id, ),) = execute(_INSERT_SOURCE, **data)
            log.info(f'added source: source_id={source_id}')
        return source_id

    @classmethod
    def remove(cls, source_id: int) -> None:
        """Purge the source record for `source_id`."""
        execute(_REMOVE_SOURCE, source_id=source_id)


class ObservationTypeNotFound(RecordNotFound):
    """The observation_type was not found in the database."""


_UPDATE_OBSERVATION_TYPE = """\
INSERT INTO "observation"."observation_type" (observation_type_id, observation_type_name,
                                              observation_type_units, observation_type_description)
VALUES (:observation_type_id, :observation_type_name, :observation_type_units, :observation_type_description)
ON CONFLICT (observation_type_id) DO UPDATE
    SET observation_type_name        = excluded.observation_type_name,
        observation_type_units       = excluded.observation_type_units,
        observation_type_description = excluded.observation_type_description;
"""


_INSERT_OBSERVATION_TYPE = """\
INSERT INTO "observation"."observation_type" (observation_type_name, observation_type_units,
                                              observation_type_description)
VALUES (:observation_type_name, :observation_type_units, :observation_type_description)
RETURNING observation_type_id;
"""


_REMOVE_OBSERVATION_TYPE = """\
DELETE FROM "observation"."observation_type"
WHERE observation_type_id = :observation_type_id;
"""


class ObservationType(Record):
    """
    A record from the "observation"."observation_type" table.

    Example
    -------
    >>> from refitt.database.observation import ObservationType
    >>> ObservationType.from_name('g-ztf')
    ObservationType(observation_type_id=1,
                    observation_type_name='g-ztf',
                    observation_type_units='magnitude',
                    observation_type_description='G-band apparent magnitude (ZTF).')
    """

    _fields = ('observation_type_id', 'observation_type_name', 'observation_type_units',
               'observation_type_description')
    _masked = False

    _observation_type_id: Optional[int] = None
    _observation_type_name: str = None
    _observation_type_units: str = None
    _observation_type_description: str = None

    _FACTORIES = {'observation_type_id': 'from_id', 'observation_type_name': 'from_name', }

    @property
    def observation_type_id(self) -> Optional[int]:
        return self._observation_type_id

    @observation_type_id.setter
    def observation_type_id(self, value: int) -> None:
        _observation_type_id = None if value is None else int(value)
        if _observation_type_id is not None and _observation_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_type_id expects positive integer')
        else:
            self._observation_type_id = _observation_type_id

    @property
    def observation_type_name(self) -> str:
        return self._observation_type_name

    @observation_type_name.setter
    def observation_type_name(self, value: str) -> None:
        self._observation_type_name = str(value)

    @property
    def observation_type_units(self) -> str:
        return self._observation_type_units

    @observation_type_units.setter
    def observation_type_units(self, value: str) -> None:
        self._observation_type_units = str(value)

    @property
    def observation_type_description(self) -> str:
        return self._observation_type_description

    @observation_type_description.setter
    def observation_type_description(self, value: str) -> None:
        self._observation_type_description = str(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> ObservationType:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise ObservationTypeNotFound(*error.args) from error

    @classmethod
    def from_id(cls, observation_type_id: int, interface: Interface = None) -> ObservationType:
        """Get observation_type record from `observation_type_id`."""
        return cls._from_unique(observation_type, 'observation_type_id', observation_type_id, interface)

    @classmethod
    def from_name(cls, observation_type_name: int, interface: Interface = None) -> ObservationType:
        """Get observation_type record from `observation_type_name`."""
        return cls._from_unique(observation_type, 'observation_type_name', observation_type_name, interface)

    def to_database(self) -> int:
        """Add observation_type record to the database."""
        data = self.to_dict()
        observation_type_id = data.pop('observation_type_id')
        if observation_type_id:
            execute(_UPDATE_OBSERVATION_TYPE, observation_type_id=observation_type_id, **data)
            log.info(f'updated source_type: observation_type_id={observation_type_id}')
        else:
            ((observation_type_id, ),) = execute(_INSERT_OBSERVATION_TYPE, **data)
            log.info(f'added source_type: observation_type_id={observation_type_id}')
        return observation_type_id

    @classmethod
    def remove(cls, observation_type_id: int) -> None:
        """Purge the observation_type record for `observation_type_id`."""
        execute(_REMOVE_OBSERVATION_TYPE, observation_type_id=observation_type_id)


class ObservationNotFound(RecordNotFound):
    """The observation was not found in the database."""


_UPDATE_OBSERVATION = """\
INSERT INTO "observation"."observation" (observation_id, object_id, observation_type_id,
                                         source_id, observation_time, observation_value,
                                         observation_error, observation_recorded)
VALUES (:observation_id, :object_id, :observation_type_id, :source_id, :observation_time,
        :observation_value, :observation_error, :observation_recorded)
ON CONFLICT (observation_id) DO UPDATE
    SET object_id            = excluded.object_id,
        observation_type_id  = excluded.observation_type_id,
        source_id            = excluded.source_id,
        observation_time     = excluded.observation_time,
        observation_value    = excluded.observation_value,
        observation_recorded = excluded.observation_recorded;

"""


_INSERT_OBSERVATION = """\
INSERT INTO "observation"."observation" (object_id, observation_type_id, source_id,
                                         observation_time, observation_value,
                                         observation_error)
VALUES (:object_id, :observation_type_id, :source_id, :observation_time,
        :observation_value, :observation_error)
RETURNING observation_id;
"""


_REMOVE_OBSERVATION = """\
DELETE FROM "observation"."observation"
WHERE observation_id = :observation_id;
"""


class Observation(Record):
    """
    A record from the "observation"."observation" table.
    """

    _fields = ('observation_id', 'object_id', 'observation_type_id',
               'source_id', 'observation_time', 'observation_value',
               'observation_error', 'observation_recorded')
    _masked = False

    _observation_id: Optional[int] = None
    _object_id: int = None
    _observation_type_id: int = None
    _source_id: int = None
    _observation_time: datetime = None
    _observation_value: float = None
    _observation_error: Optional[float] = None
    _observation_recorded: Optional[datetime] = None

    _FACTORIES = {'observation_id': 'from_id', }

    @property
    def observation_id(self) -> Optional[int]:
        return self._observation_id

    @observation_id.setter
    def observation_id(self, value: int) -> None:
        _observation_id = None if value is None else int(value)
        if _observation_id is not None and _observation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_id expects positive integer')
        else:
            self._observation_id = _observation_id

    @property
    def object_id(self) -> Optional[int]:
        return self._object_id

    @object_id.setter
    def object_id(self, value: int) -> None:
        _object_id = None if value is None else int(value)
        if _object_id is not None and _object_id < 0:
            raise ValueError(f'{self.__class__.__name__}.object_id expects positive integer')
        else:
            self._object_id = _object_id

    @property
    def observation_type_id(self) -> Optional[int]:
        return self._observation_type_id

    @observation_type_id.setter
    def observation_type_id(self, value: int) -> None:
        _observation_type_id = None if value is None else int(value)
        if _observation_type_id is not None and _observation_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_type_id expects positive integer')
        else:
            self._observation_type_id = _observation_type_id

    @property
    def source_id(self) -> Optional[int]:
        return self._source_id

    @source_id.setter
    def source_id(self, value: int) -> None:
        _source_id = None if value is None else int(value)
        if _source_id is not None and _source_id < 0:
            raise ValueError(f'{self.__class__.__name__}.source_id expects positive integer')
        else:
            self._source_id = _source_id

    @property
    def observation_time(self) -> datetime:
        return self._observation_time

    @observation_time.setter
    def observation_time(self, value: datetime) -> None:
        _observation_time = value
        if not isinstance(_observation_time, datetime):
            raise TypeError(f'{self.__class__.__name__}.observation_time expects datetime.datetime')
        else:
            self._observation_time = _observation_time

    @property
    def observation_value(self) -> Optional[int]:
        return self._observation_value

    @observation_value.setter
    def observation_value(self, value: int) -> None:
        self._observation_value = float(value)

    @property
    def observation_error(self) -> Optional[int]:
        return self._observation_error

    @observation_error.setter
    def observation_error(self, value: int) -> None:
        self._observation_error = float(value)

    @property
    def observation_recorded(self) -> Optional[datetime]:
        return self._observation_recorded

    @observation_recorded.setter
    def observation_recorded(self, value: datetime) -> None:
        if value is None:
            self._observation_recorded = None
        else:
            _observation_recorded = value
            if not isinstance(_observation_recorded, datetime):
                raise TypeError(f'{self.__class__.__name__}.observation_recorded expects datetime.datetime')
            else:
                self._observation_recorded = _observation_recorded

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Observation:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise ObservationNotFound(*error.args) from error

    @classmethod
    def from_id(cls, observation_id: int, interface: Interface = None) -> Observation:
        """Get observation record from `observation_id`."""
        return cls._from_unique(observation, 'observation_id', observation_id, interface)

    def to_database(self) -> int:
        """Add observation record to the database."""
        data = self.to_dict()
        observation_id = data.pop('observation_id')
        if observation_id:
            execute(_UPDATE_OBSERVATION, observation_id=observation_id, **data)
            log.info(f'updated observation: observation_id={observation_id}')
        else:
            ((observation_id, ),) = execute(_INSERT_OBSERVATION, **data)
            log.info(f'added observation: observation_id={observation_id}')
        return observation_id

    @classmethod
    def remove(cls, observation_id: int) -> None:
        """Purge the observation record for `observation_id`."""
        execute(_REMOVE_OBSERVATION, observation_id=observation_id)


class AlertNotFound(RecordNotFound):
    """The alert was not found in the database."""


_UPDATE_ALERT = """\
INSERT INTO "observation"."alert" (alert_id, observation_id, alert_data)
VALUES (:alert_id, :observation_id, :alert_data)
ON CONFLICT (alert_id) DO UPDATE
    SET observation_id = excluded.observation_id,
        alert_data     = excluded.alert_data;

"""


_INSERT_ALERT = """\
INSERT INTO "observation"."alert" (observation_id, alert_data)
VALUES (:observation_id, :alert_data)
RETURNING alert_id;
"""


_REMOVE_ALERT = """\
DELETE FROM "observation"."alert"
WHERE alert_id = :alert_id;
"""


class Alert(Record):
    """
    A record from the "observation"."alert" table.
    """

    _fields = ('alert_id', 'observation_id', 'alert_data')
    _masked = False

    _alert_id: Optional[int] = None
    _observation_id: int = None
    _alert_data: dict = None

    _FACTORIES = {'alert_id': 'from_id', 'observation_id': 'from_observation'}

    @property
    def alert_id(self) -> Optional[int]:
        return self._alert_id

    @alert_id.setter
    def alert_id(self, value: int) -> None:
        _alert_id = None if value is None else int(value)
        if _alert_id is not None and _alert_id < 0:
            raise ValueError(f'{self.__class__.__name__}.alert_id expects positive integer')
        else:
            self._alert_id = _alert_id

    @property
    def observation_id(self) -> Optional[int]:
        return self._observation_id

    @observation_id.setter
    def observation_id(self, value: int) -> None:
        _observation_id = None if value is None else int(value)
        if _observation_id is not None and _observation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_id expects positive integer')
        else:
            self._observation_id = _observation_id

    @property
    def alert_data(self) -> dict:
        return self._alert_data

    @alert_data.setter
    def alert_data(self, other: dict) -> None:
        self._alert_data = dict(other)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Alert:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise AlertNotFound(*error.args) from error

    @classmethod
    def from_id(cls, alert_id: int, interface: Interface = None) -> Alert:
        """Get alert record from `alert_id`."""
        return cls._from_unique(alert, 'alert_id', alert_id, interface)

    @classmethod
    def from_observation(cls, observation_id: int, interface: Interface = None) -> Alert:
        """Get alert record from `observation_id`."""
        return cls._from_unique(alert, 'observation_id', observation_id, interface)

    def to_database(self) -> int:
        """Add alert record to the database."""
        data = self.to_dict()
        data['alert_data'] = json.dumps(data['alert_data'])
        alert_id = data.pop('alert_id')
        if alert_id:
            execute(_UPDATE_ALERT, alert_id=alert_id, **data)
            log.info(f'updated alert: alert_id={alert_id}')
        else:
            ((alert_id, ),) = execute(_INSERT_ALERT, **data)
            log.info(f'added alert: alert_id={alert_id}')
        return alert_id

    @classmethod
    def remove(cls, observation_type_id: int) -> None:
        """Purge the observation_type record for `observation_type_id`."""
        execute(_REMOVE_ALERT, observation_type_id=observation_type_id)


class FileNotFound(RecordNotFound):
    """The file was not found in the database."""


_UPDATE_FILE = """\
INSERT INTO "observation"."file" (file_id, observation_id, file_data, file_type)
VALUES (:file_id, :observation_id, :file_data, :file_type)
ON CONFLICT (file_id) DO UPDATE
    SET observation_id = excluded.observation_id,
        file_data      = excluded.file_data,
        file_type      = excluded.file_type;

"""


_INSERT_FILE = """\
INSERT INTO "observation"."file" (observation_id, file_data, file_type)
VALUES (:observation_id, :file_data, :file_type)
RETURNING file_id;
"""


_REMOVE_FILE = """\
DELETE FROM "observation"."file"
WHERE file_id = :file_id;
"""


class File(Record):
    """
    A record from the "observation"."file" table.
    """

    _fields = ('file_id', 'observation_id', 'file_data', 'file_type')
    _masked = False

    _file_id: Optional[int] = None
    _observation_id: int = None
    _file_data: bytes = None
    _file_type: str = None

    _FACTORIES = {'file_id': 'from_id', 'observation_id': 'from_observation'}

    @property
    def file_id(self) -> Optional[int]:
        return self._file_id

    @file_id.setter
    def file_id(self, value: int) -> None:
        _file_id = None if value is None else int(value)
        if _file_id is not None and _file_id < 0:
            raise ValueError(f'{self.__class__.__name__}.file_id expects positive integer')
        else:
            self._file_id = _file_id

    @property
    def observation_id(self) -> Optional[int]:
        return self._observation_id

    @observation_id.setter
    def observation_id(self, value: int) -> None:
        _observation_id = None if value is None else int(value)
        if _observation_id is not None and _observation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_id expects positive integer')
        else:
            self._observation_id = _observation_id

    @property
    def file_data(self) -> bytes:
        return self._file_data

    @file_data.setter
    def file_data(self, value: bytes) -> None:
        if isinstance(value, bytes):
            self._file_data = value
        elif isinstance(value, str):
            self._file_data = value.encode('utf-8')
        else:
            raise TypeError(f'{self.__class__.__name__}.file_data expects bytes or str.')

    @property
    def file_type(self) -> str:
        return self._file_type

    @file_type.setter
    def file_type(self, value: str) -> None:
        self._file_type = str(value)

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> file:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise FileNotFound(*error.args) from error

    @classmethod
    def from_id(cls, file_id: int, interface: Interface = None) -> File:
        """Get file record from `file_id`."""
        return cls._from_unique(file, 'file_id', file_id, interface)

    @classmethod
    def from_observation(cls, observation_id: int, interface: Interface = None) -> File:
        """Get file record from `observation_id`."""
        return cls._from_unique(file, 'observation_id', observation_id, interface)

    def to_database(self) -> int:
        """Add file record to the database."""
        data = self.to_dict()
        file_id = data.pop('file_id')
        if file_id:
            execute(_UPDATE_FILE, file_id=file_id, **data)
            log.info(f'updated file: file_id={file_id}')
        else:
            ((file_id, ),) = execute(_INSERT_FILE, **data)
            log.info(f'added file: file_id={file_id}')
        return file_id

    @classmethod
    def from_database(cls, *args, **kwargs) -> File:
        """Override base method to convert bytearray into bytes."""
        record = super().from_database(*args, **kwargs)
        record.file_data

    @classmethod
    def remove(cls, file_id: int) -> None:
        """Purge the file record for `file_id`."""
        execute(_REMOVE_FILE, file_id=file_id)
