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

"""Forecast data structure."""


# type annotations
from __future__ import annotations
from typing import Dict, Union, Any, IO

# standard libs
import json
import logging
from datetime import datetime
from functools import cached_property, lru_cache

# external libs
from astropy.time import Time

# internal libs
from ..core.schema import ListSchema, DictSchema
from ..database.model import Object, Source, ObservationType, Observation, Forecast as ForecastModel

# public interface
__all__ = ['Forecast', ]

# initialize module level logger
log = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_type_id(type_name: str) -> int:
    """Query database for `observation_type.id` based on `observation_type.name`."""
    return ObservationType.from_name(type_name).id


@lru_cache(maxsize=None)
def get_source_id(name: str = 'refitt') -> int:
    """Query database for `source.id` from `source.name`."""
    return Source.from_name(name).id


class Forecast:
    """High-level interface for manipulating forecast data."""

    __data: dict
    schema = DictSchema.of({
        "ztf_id": str,
        "instrument": str,
        "time_since_trigger": float,
        "current_time": float,
        "num_obs": int,
        "filter": str,  # e.g., "ztf-g"
        "class": ListSchema.any(),  # FIXME: we should use a different structure here
        "phase": str,
        "next_mag_mean": float,
        "next_mag_sigma": float,
        "time_to_peak": ListSchema.of(float),
        "time_arr": ListSchema.of(float),
        "mag_mean": ListSchema.of(float),
        "mag_sigma": ListSchema.of(float),
        "mdmc": float,
        "moe": float
    })

    def __init__(self, data: Union[Forecast, dict]) -> None:
        """Directly initialize with `data`."""
        if isinstance(data, (Forecast, dict)):
            self.data = data if isinstance(data, dict) else data.data
        else:
            raise TypeError(f'Cannot initialize Forecast data with type {data.__class__.__name__}')

    @property
    def data(self) -> dict:
        return self.__data

    @data.setter
    def data(self, other: dict) -> None:
        self.__data = self.schema.ensure(other)

    def __getattr__(self, key: str) -> Any:
        return self.data[key]

    def __str__(self) -> str:
        """View forecast in string (JSON) form."""
        return repr(self.data)

    def __repr__(self) -> str:
        """Interactive representation."""
        return f'<Forecast({self})>'

    def __eq__(self, other: Forecast) -> bool:
        """The forecasts are equal if the data are equal."""
        return isinstance(other, Forecast) and self.data == other.data

    def __ne__(self, other: Forecast) -> bool:
        """The forecasts are not equal if the data are not equal."""
        return not self == other

    @classmethod
    def from_dict(cls, data: dict) -> Forecast:
        """Create forecast from raw `data` (JSON)."""
        return cls(data)

    def to_dict(self) -> dict:
        """Dump forecast to dictionary."""
        return self.data.copy()

    @classmethod
    def from_str(cls, text: str, **options) -> Forecast:
        """Create forecast from raw `text` data."""
        return cls.from_dict(json.loads(text, **options))

    @classmethod
    def from_io(cls, stream: IO) -> Forecast:
        """Create forecast reading text from existing IO `stream` (e.g., sys.stdin)."""
        return cls.from_str(stream.read())

    @classmethod
    def from_local(cls, filepath: str, **options) -> Forecast:
        """Load forecast from local `filepath`."""
        with open(filepath, mode='r', **options) as stream:
            return cls.from_io(stream)

    def to_local(self, filepath: str, indent: int = 4, **options) -> None:
        """Write forecast to local `filepath`."""
        with open(filepath, mode='w') as output:
            json.dump(self.to_dict(), output, indent=indent, **options)

    @cached_property
    def time(self) -> datetime:
        """MJD plus one day."""
        return Time(self.current_time + 1, format='mjd', scale='utc').datetime

    @cached_property
    def object_id(self) -> int:
        """Object ID for REFITT from ZTF ID."""
        return Object.from_alias(ztf=self.ztf_id).id

    @cached_property
    def observation_data(self) -> Dict[str, Any]:
        """Generated Observation records for this forecast."""
        return {'type_id': get_type_id(self.filter),
                'object_id': self.object_id,
                'source_id': get_source_id(),
                'value': self.next_mag_mean,
                'error': self.next_mag_sigma,
                'time': self.time}

    def publish(self) -> ForecastModel:
        """Construct forecast record and insert into database."""
        return ForecastModel.add({'observation_id': Observation.add(self.observation_data).id,
                                  'data': self.to_dict()})
