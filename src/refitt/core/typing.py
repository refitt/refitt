# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core typing methods and annotation type definitions."""


# type annotations
from typing import Dict, List, Union, Any

# standard libs
from datetime import datetime

# public interface
__all__ = ['coerce', 'coerce_json',
           'ValueType', 'JSONValue', 'JsonObject', 'JsonArray', 'JsonDict']


# Core value types
ValueType = Union[bool, str, int, float, datetime, None]


# JSON structures (so much can be said here: https://github.com/python/typing/issues/182)
JSONValue = Union[bool, str, int, float, None]
JsonObject = Union[JSONValue, Dict[str, Any], List[Any]]
JsonArray = List[JsonObject]
JsonDict = Dict[str, JsonObject]


def coerce(value: str) -> ValueType:
    """Automatically coerce string to typed value."""
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return coerce_json(value)


def coerce_json(value: str) -> JSONValue:
    """Automatically coerce string to JSON-serializable typed value."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() in ('null', 'none', ):
        return None
    elif value.lower() in ('true', ):
        return True
    elif value.lower() in ('false', ):
        return False
    else:
        return value
