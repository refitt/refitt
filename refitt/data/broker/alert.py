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

"""Implements the common `Alert` interface for all broker clients."""

# type annotations
from __future__ import annotations
from typing import List, Dict, Union, Any, Optional

# standard libs
import json
from datetime import datetime
from abc import ABC, abstractmethod

# internal libs
from ...database.model import ObjectType, Object, Source, ObservationType, Observation, Alert
from ...database.core import Session


# JSON-dict
AlertJSON = Dict[str, Any]


class AlertInterface(ABC):
    """High-level interface to JSON alert objects."""

    _data: AlertJSON = {}
    _record: Optional[Alert] = None
    previous: List[AlertInterface] = []

    def __init__(self, data: Union[AlertJSON, AlertInterface]) -> None:
        """Initialize with existing data."""
        self.data = data
        self.previous = []

    @property
    def data(self) -> AlertJSON:
        """Access to underlying alert data."""
        return self._data

    @data.setter
    def data(self, other: AlertJSON) -> None:
        """Set underlying alert data."""
        if isinstance(other, self.__class__):
            self._data = other._data
            self.previous = other.previous
        elif isinstance(other, dict):
            self._data = other
        else:
            raise TypeError(f'{self.__class__.__name__}.data expects {dict}')

    def __getitem__(self, key: str) -> Any:
        """Get item from Alert data."""
        return self.data[key]

    @classmethod
    def from_dict(cls, data: AlertJSON) -> AlertInterface:
        """Create alert from raw `data` (JSON)."""
        return cls(data)

    @classmethod
    def from_local(cls, path: str, **options) -> AlertInterface:
        """Load an Alert from local `path`."""
        with open(path, mode='r') as source:
            return cls.from_dict(json.load(source, **options))

    def to_local(self, path: str, indent: int = 4, **options) -> None:
        """Write alert to local `path`."""
        with open(path, mode='w') as output:
            json.dump(self.data, output, indent=indent, **options)

    def __str__(self) -> str:
        """View alert in string (JSON) form."""
        return repr(self.data)

    def __repr__(self) -> str:
        """Interactive representation."""
        return f'<{self.__class__.__name__}({self})>'

    def __eq__(self, other: AlertInterface) -> bool:
        """The alerts are equal if the data are equal."""
        return isinstance(other, AlertInterface) and self.data == other.data

    def __ne__(self, other: AlertInterface) -> bool:
        """The alerts are equal if the data are equal."""
        return not self == other

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def source_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {}

    @property
    @abstractmethod
    def object_type_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def object_ra(self) -> float:
        raise NotImplementedError()

    @property
    @abstractmethod
    def object_dec(self) -> float:
        raise NotImplementedError()

    @property
    @abstractmethod
    def object_redshift(self) -> float:
        raise NotImplementedError()

    @property
    @abstractmethod
    def observation_type_name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def observation_value(self) -> float:
        raise NotImplementedError()

    @property
    @abstractmethod
    def observation_error(self) -> float:
        raise NotImplementedError()

    @property
    @abstractmethod
    def observation_time(self) -> datetime:
        raise NotImplementedError()

    def to_database(self) -> Alert:
        """Create an Object, Observation, and Alert record and write to the database."""
        session = Session()
        try:
            return self._to_database(session)
        except Exception:
            session.rollback()
            raise

    def _to_database(self, session: Session) -> Alert:
        """Implementation of `to_database`."""
        object_type_id = self._get_object_type_id(session)
        object_id = self._get_object_id(object_type_id, session)
        obs_type_id = self._get_observation_type(session)
        observation_id = self._create_observation(object_id, obs_type_id, session)
        self._record = Alert.add({'observation_id': observation_id, 'data': self.data})
        return self._record

    def _create_observation(self, object_id: int, obs_type_id: int, session: Session) -> int:
        """Add observation to database and return new observation id."""
        observation = Observation.add({'object_id': object_id, 'type_id': obs_type_id,
                                       'source_id': Source.from_name(self.source_name, session).id,
                                       'value': self.observation_value, 'error': self.observation_error,
                                       'time': self.observation_time}, session)
        return observation.id

    def _get_observation_type(self, session: Session) -> int:
        """"""
        try:
            obs_type = ObservationType.from_name(self.observation_type_name, session)
        except ObservationType.NotFound:
            obs_type = ObservationType(name=self.observation_type_name,
                                       description=f'Type specified by source={self.source_name}')
            session.add(obs_type)
            session.commit()
        return obs_type.id

    def _get_object_id(self, object_type_id: int, session: Session) -> int:
        """
        Check for existing object by aliases or create new object if necessary.

        Returns:
            object_id (int):
                The object ID for an existing or newly created object.
        """
        for provider, name in self.object_aliases.items():
            try:
                object = Object.from_alias(session, **{provider: name})
                break
            except Object.NotFound:
                pass
        else:
            object = Object.add({'type_id': object_type_id, 'aliases': self.object_aliases,
                                 'ra': self.object_ra, 'dec': self.object_dec,
                                 'redshift': self.object_redshift}, session)
        return object.id

    def _get_object_type_id(self, session: Session) -> int:
        """
        Check object type and persist to database if necessary.

        Returns:
            object_type_id (int):
                The existing, or newly created, object_type_id.
        """
        if self.object_type_name is None:
            object_type_id = ObjectType.from_name('Unknown', session)
        else:
            try:
                object_type = ObjectType.from_name(self.object_type_name, session)
                object_type_id = object_type.id
            except ObjectType.NotFound:
                object_type = ObjectType(name=self.object_type_name,
                                         description=f'Type specified by source={self.source_name}')
                session.add(object_type)
                session.commit()
                object_type_id = object_type.id
        return object_type_id

    def backfill_database(self) -> List[Alert]:
        """
        Retroactively fill database with an alert's available prior history.

        Note:
            The method calls :meth:`to_database` automatically if necessary.
        """
        latest = self._record or self.to_database()
        query = Session.query(Observation).filter(Observation.object_id == latest.observation.object.id,
                                                  Observation.source_id == latest.observation.source.id)
        observation_times = [observation.time.astimezone() for observation in query.all()]
        alert_times = [alert.observation_time.astimezone() for alert in self.previous]
        missing_alerts = [alert for alert, time in zip(self.previous, alert_times) if time not in observation_times]
        return [alert.to_database() for alert in missing_alerts]
