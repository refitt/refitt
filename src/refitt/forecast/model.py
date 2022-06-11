# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Abstract model data interface."""


# type annotations
from __future__ import annotations
from typing import Set, Union, Type, IO, Optional

# standard libs
import json
import functools
from datetime import datetime
from abc import ABC, abstractmethod

# external libs
from astropy.time import Time

# internal libs
from refitt.core.schema import DictSchema, SchemaDefinitionError
from refitt.core.typing import JsonDict, JsonObject
from refitt.database.model import Model as ModelRecord, ModelType, Epoch, Source, Object, ObservationType, Observation

# public interface
__all__ = ['ModelData', 'ModelSchema', ]


@functools.lru_cache(maxsize=None)
def get_epoch_id() -> int:
    """Fetch and cache the latest epoch id."""
    return Epoch.latest().id


@functools.lru_cache(maxsize=None)
def get_model_type_id(name: str) -> int:
    """Fetch and cache `model_type.id` given `name`."""
    return ModelType.from_name(name).id


@functools.lru_cache(maxsize=None)
def get_source_id(name: str) -> int:
    """Fetch and cache `source.id` given `name`."""
    return Source.from_name(name).id


@functools.lru_cache(maxsize=None)
def get_observation_type_id(name: str) -> int:
    """Fetch and cache `observation_type.id` given `name`."""
    return ObservationType.from_name(name).id


class ModelSchema(DictSchema):
    """Enforce minimum schema requirements for model data."""

    _required_keys: Set[str] = {
        'model_type',  # str
        'ztf_id',      # str
        'filter',      # str
        'mjd_arr',     # list[float]
        'mag_arr',     # list[float] | list[list[float]]
        'mjd',         # float
    }

    class DefinitionError(SchemaDefinitionError):
        """Violation of schema requirements."""

    def __init__(self, member_type: dict) -> None:
        """Ensure schema requirements for model."""
        super().__init__(member_type)
        for key in self._required_keys:
            if key not in member_type:
                raise self.DefinitionError(f'Required key \'{key}\' not found')


class ModelData(ABC):
    """Interface for model schema and data management."""

    __data: JsonDict

    class Error(Exception):
        """Errors common to model data interface."""

    @property
    @abstractmethod
    def name(self: ModelData) -> str:
        """The unique name defining this forecast type in the database."""

    @property
    @abstractmethod
    def schema(self: ModelData) -> ModelSchema:
        """Schema definition for model data."""

    def __init__(self, data: Union[ModelData, JsonDict]) -> None:
        """Directly initialize with `data`."""
        if isinstance(data, (type(self), dict)):
            self.data = data if isinstance(data, dict) else data.data
        else:
            raise TypeError(f'Cannot initialize {self.__class__.__name__} data with type'
                            f' {data.__class__.__name__}')

    @property
    def data(self: ModelData) -> JsonDict:
        """Direct access to underlying JSON data."""
        return self.__data

    @data.setter
    def data(self: ModelData, other: JsonDict) -> None:
        """Assign underlying JSON data."""
        self.__data = self.schema.ensure(other)

    def __getattr__(self: ModelData, key: str) -> JsonObject:
        """Access internal data with dot-notation."""
        return self.data[key]

    def __str__(self: ModelData) -> str:
        """View model data in string (JSON) form."""
        return repr(self.data)

    def __repr__(self: ModelData) -> str:
        """Interactive representation."""
        return f'<{self.__class__.__name__}({self})>'

    def __eq__(self: ModelData, other: ModelData) -> bool:
        """The models are equal if the data are equal."""
        return isinstance(other, type(self)) and self.data == other.data

    def __ne__(self: ModelData, other: ModelData) -> bool:
        """The models are not equal if the data are not equal."""
        return not self == other

    @classmethod
    def from_dict(cls: Type[ModelData], data: JsonDict) -> ModelData:
        """Create model data from raw `data` (JSON)."""
        return cls(data)

    @classmethod
    def from_str(cls: Type[ModelData], text: str, **options) -> ModelData:
        """Create model data from raw `text` data."""
        return cls.from_dict(json.loads(text, **options))

    @classmethod
    def from_io(cls: Type[ModelData], stream: IO) -> ModelData:
        """Create model data by reading text from existing IO `stream` (e.g., sys.stdin)."""
        return cls.from_str(stream.read())

    @classmethod
    def from_local(cls: Type[ModelData], filepath: str, **options) -> ModelData:
        """Load model data from local `filepath`."""
        with open(filepath, mode='r', **options) as stream:
            return cls.from_io(stream)

    def to_dict(self: ModelData) -> JsonDict:
        """Dump model data to dictionary."""
        return self.data.copy()

    def to_local(self: ModelData, filepath: str, indent: int = 4, **options) -> None:
        """Write model data to local `filepath`."""
        with open(filepath, mode='w') as output:
            json.dump(self.to_dict(), output, indent=indent, **options)

    def publish(self: ModelData, observation_id: int = None, epoch_id: int = None) -> ModelRecord:
        """Construct and publish records to database."""
        if not observation_id:
            observation_id = self.publish_observation(epoch_id).id
        return ModelRecord.add({
            'epoch_id': epoch_id or get_epoch_id(),
            'type_id': get_model_type_id(self.name),
            'observation_id': observation_id,
            'data': self.to_dict()
        })

    def publish_observation(self: ModelData, epoch_id: int = None) -> Observation:
        """Publish synthetic observation for this model to the database."""
        return Observation.add({
            'epoch_id': epoch_id or get_epoch_id(),
            'type_id': get_observation_type_id(self.filter),
            'object_id': self.object_id,
            'source_id': get_source_id('refitt'),
            'value': self.observation_value,
            'error': self.observation_error,
            'time': self.observation_time,
        })

    @functools.cached_property
    def object_id(self: ModelData) -> int:
        """Object ID for REFITT from ZTF ID."""
        return Object.from_alias(ztf=self.ztf_id).id

    @functools.cached_property
    def observation_time(self: ModelData) -> datetime:
        """MJD plus one day."""
        return Time(self.mjd + 1, format='mjd', scale='utc').datetime

    @property
    @abstractmethod
    def observation_value(self: ModelData) -> Optional[float]:
        """Value for published observation record."""

    @property
    @abstractmethod
    def observation_error(self: ModelData) -> Optional[float]:
        """Error for published observation record."""

    @property
    @abstractmethod
    def object_pred_type(self: ModelData) -> Optional[dict]:
        """Predicted object type (e.g., {'id': 42, 'name': 'SN Ia', 'score': 0.7931})."""
