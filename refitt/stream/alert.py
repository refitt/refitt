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

# standard libs
import json
from abc import ABC, abstractproperty
from typing import Dict, Any


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
    def alert_id(self) -> int:
        """Unique identifier from this alert."""

    @classmethod
    def from_dict(cls, data: AlertJSON) -> 'AlertInterface':
        """Create alert from raw `data` (JSON)."""
        return cls(data)

    @classmethod
    def from_file(cls, filepath: str, **options) -> 'AlertInterface':
        """Load an Alert from local `filepath`."""
        with open(filepath, mode='r') as source:
            return cls(json.load(source, **options))

    def to_file(self, filepath: str, indent: int = 4, **options) -> None:
        """Write alert to local `filepath`."""
        with open(filepath, mode='w') as output:
            json.dump(self.data, output, indent=indent, **options)

    @classmethod
    def from_str(cls, value: str, **options) -> 'AlertInterface':
        """Load an alert from existing string (JSON)."""
        return cls(json.loads(value, **options))
    
    def to_str(self, indent: int = 4, **options) -> str:
        """Convert alert to string (JSON) format."""
        return json.dumps(self.data, indent=indent, **options)
    
    def __str__(self) -> str:
        """View alert in string (JSON) form."""
        return self.to_str(indent=4)
    
    def __repr__(self) -> str:
        """Interactive representation (JSON)."""
        return str(self)