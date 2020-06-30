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
from typing import Dict, Union, Any

# standard libs
import json
from datetime import datetime
from functools import lru_cache
from abc import ABC, abstractproperty

# internal libs
from ..database import client
from ..database.observation import (Object as _Object, Alert as _Alert, Source, Observation,
                                    ObservationType, ObservationTypeNotFound,
                                    ObjectType, ObjectTypeNotFound)


# JSON-dict
AlertJSON = Dict[str, Any]


class AlertInterface:
    """High-level interface to JSON alert objects."""

    _data: AlertJSON = {}

    def __init__(self, data: AlertJSON) -> None:
        """Initialize with existing data."""
        self.data = data

    @property
    def data(self) -> AlertJSON:
        """Access to underlying alert data."""
        return self._data

    @data.setter
    def data(self, other: AlertJSON) -> None:
        """Set underlying alert data."""
        if isinstance(other, self.__class__):
            self._data = other._data
        elif isinstance(other, dict):
            self._data = other
        else:
            raise TypeError(f'{self.__class__.__name__}.data expects {dict}.')

    @abstractproperty
    def source_name(self) -> str:
        return None

    @property
    @lru_cache(maxsize=None)
    def source_id(self) -> int:
        return Source.from_name(self.source_name).source_id

    @abstractproperty
    def object_name(self) -> str:
        return None

    @abstractproperty
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {}

    @abstractproperty
    def object_type_name(self) -> str:
        return None

    @abstractproperty
    def object_ra(self) -> float:
        return None

    @abstractproperty
    def object_dec(self) -> float:
        return None

    @abstractproperty
    def object_redshift(self) -> float:
        return None

    @abstractproperty
    def observation_type_name(self) -> str:
        return None

    @abstractproperty
    def observation_value(self) -> float:
        return None

    @abstractproperty
    def observation_error(self) -> float:
        return None

    @abstractproperty
    def observation_time(self) -> datetime:
        return None

    def to_database(self) -> None:
        """Create an Object, Observation, and Alert record and write to the database."""

        if self.object_type_name is None:
            object_type_id = 0  # "UNKNOWN" in database
        else:
            try:
                object_type = ObjectType.from_name(self.object_type_name)
                object_type_id = object_type.object_type_id
            except ObjectTypeNotFound:
                object_type = ObjectType(object_type_name=self.object_type_name,
                                         object_type_description=None)
                object_type_id = object_type.to_database()

        obj = _Object(object_type_id=object_type_id, object_name=self.object_name,
                      object_aliases=self.object_aliases, object_ra=self.object_ra,
                      object_dec=self.object_dec, object_redshift=self.object_redshift,
                      object_metadata={})
        object_id = obj.to_database()

        observation_type = ObservationType.from_name(self.observation_type_name)
        observation_type_id = observation_type.observation_type_id
        observation = Observation(object_id=object_id,
                                  observation_type_id=observation_type_id,
                                  source_id=self.source_id,
                                  observation_value=self.observation_value,
                                  observation_time=self.observation_time,
                                  observation_error=self.observation_error,
                                  observation_recorded=None)

        observation_id = observation.to_database()
        alert = _Alert(observation_id=observation_id, alert_data=self.data)
        alert_id = alert.to_database()
        return observation_id, alert_id

    def __getitem__(self, key: str) -> Any:
        """Get item from Alert data."""
        return self.data[key]

    @classmethod
    def from_dict(cls, data: AlertJSON) -> 'AlertInterface':
        """Create alert from raw `data` (JSON)."""
        return cls(data)

    @classmethod
    def from_file(cls, filepath: str, **options) -> AlertInterface:
        """Load an Alert from local `filepath`."""
        with open(filepath, mode='r') as source:
            return cls(json.load(source, **options))

    def to_file(self, filepath: str, indent: int = 4, **options) -> None:
        """Write alert to local `filepath`."""
        with open(filepath, mode='w') as output:
            json.dump(self.data, output, indent=indent, **options)

    @classmethod
    def from_str(cls, value: str, **options) -> AlertInterface:
        """Load an alert from existing string (JSON)."""
        return cls(json.loads(value, **options))

    def to_str(self, indent: int = None, **options) -> str:
        """Convert alert to string (JSON) format."""
        return json.dumps(self.data, indent=indent, **options)

    def __str__(self) -> str:
        """View alert in string (JSON) form."""
        return self.to_str(indent=4)

    def __repr__(self) -> str:
        """Interactive representation (JSON)."""
        return str(self)
