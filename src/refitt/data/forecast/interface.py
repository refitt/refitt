# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Abstract model data interface."""


# type annotations
from __future__ import annotations
from typing import Union, Type, IO

# standard libs
import json
from abc import ABC, abstractproperty, abstractmethod

# internal libs
from ...core.schema import DictSchema
from ...core.typing import JsonDict, JsonObject
from ...database.model import Model as ModelRecord

# public interface
__all__ = ['ModelData', ]


class ModelData(ABC):
    """Interface for model schema and data management."""

    __data: JsonDict

    @abstractproperty
    def schema(self: ModelData) -> DictSchema:
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

    @abstractmethod
    def publish(self: ModelData) -> ModelRecord:
        """Construct database record and publish to database."""
