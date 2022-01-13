# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Forecast model data schema, interface, and publishing."""


# type annotations
from __future__ import annotations
from typing import Dict, Any

# standard libs
from datetime import datetime
from functools import cached_property, lru_cache

# external libs
from astropy.time import Time

# internal libs
from ...core.schema import ListSchema, DictSchema
from ...database.model import Object, Source, ObservationType, Observation, Model, ModelType, Epoch
from .interface import ModelData

# public interface
__all__ = ['ForecastModel', ]


@lru_cache(maxsize=None)
def get_type_id(type_name: str) -> int:
    """Query database for `observation_type.id` based on `observation_type.name`."""
    return ObservationType.from_name(type_name).id


@lru_cache(maxsize=None)
def get_source_id(name: str = 'refitt') -> int:
    """Query database for `source.id` from `source.name`."""
    return Source.from_name(name).id


class ForecastModel(ModelData):
    """
    High-level interface for manipulating forecast data.

    The REFITT 'forecast' is the primary prediction machinery and is used
    to instantiate the underlying prediction 'observation'. This observation is
    necessary for all other model data types to be published.
    """

    schema = DictSchema.of({
        "ztf_id": str,
        "instrument": str,
        "time_since_trigger": float,
        "current_time": float,
        "num_obs": int,
        "filter": str,  # e.g., "g-ztf"
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

    def publish(self) -> Model:
        """Construct forecast record and insert into database."""
        return Model.add({
            'epoch_id': Epoch.latest().id,
            'type_id': ModelType.from_name('forecast').id,
            'observation_id': Observation.add(self.observation_data).id,
            'data': self.to_dict()})

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
        return {'epoch_id': Epoch.latest().id,
                'type_id': get_type_id(self.filter),
                'object_id': self.object_id,
                'source_id': get_source_id(),
                'value': self.next_mag_mean,
                'error': self.next_mag_sigma,
                'time': self.time}
