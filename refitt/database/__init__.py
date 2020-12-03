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

"""Database interface, models, and methods."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Any, Union, TypeVar, Type, Callable

# standard libs
import json
import logging
from base64 import decodebytes as decode_base64
from datetime import datetime

# internal libs
from .. import assets
from .core import engine, Session, config
from .model import Base, tables


# initialize module level logger
log = logging.getLogger(__name__)


def init_database() -> None:
    """Initialize all database objects."""
    log.info('Creating database objects')
    Base.metadata.create_all(engine)


def drop_database() -> None:
    """Drop all database objects."""
    log.warning('Dropping database objects')
    Base.metadata.drop_all(engine)


# JSON value types and their coerced type before loading into database
__NT = type(None)
__VT = TypeVar('__VT', __NT, bool, int, float, str, Dict[str, Any], List[str])
__RT = Union[__VT, datetime, bytes]


def __coerce_datetime(value: __VT) -> Union[__VT, datetime]:
    """Passively coerce datetime formatted strings into actual datetime values."""
    if not isinstance(value, str):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        return value


def __coerce_bytes(value: __VT) -> Union[__VT, bytes]:
    """Passively coerce string lists (base64 encoded raw data)."""
    if isinstance(value, list) and all(isinstance(member, str) for member in value):
        return decode_base64('\n'.join(value).encode())
    else:
        return value


# list of defined type coercion filters
__TF = Callable[[__VT], __RT]
__type_filters: List[__TF] = [
    __coerce_datetime, __coerce_bytes
]


def __coerce_imp(value: __VT, filters: List[__TF]) -> __RT:
    """Passively coerce value types of stored record assets to database compatible types."""
    return value if not filters else filters[0](__coerce_imp(value, filters[1:]))


def __coerce(value: __VT) -> __RT:
    """Passively coerce value types of stored record assets to database compatible types."""
    return __coerce_imp(value, __type_filters)


def __load_records(base: Type[Base], path: str) -> List[Dict[str, Any]]:
    """Load all records from JSON file `path` into model of type `base`."""
    return [base(**{k: __coerce(v) for k, v in record.items()})
            for record in json.loads(assets.load_asset(path))]


# NOTE: order matters for foreign key references
__REFS: Dict[str, List[str]] = {
    'core': ['user', 'object_type', 'level', 'topic', ],
    'test': ['facility', 'user', 'facility_map', 'client', 'session', 'object_type', 'object',
             'source_type', 'source', 'observation_type', 'observation', 'alert', 'file_type', 'file',
             'recommendation_group', 'recommendation', 'level', 'topic', ]
}


def load_records(section: str) -> None:
    """Load stored record assets from `section` into database."""
    log.info(f'Loading {section} data')
    session = Session()
    for name in __REFS[section]:
        records = __load_records(tables[name], f'database/{section}/{name}.json')
        session.add_all(records)
        session.commit()
