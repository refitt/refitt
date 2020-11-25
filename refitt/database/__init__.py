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
from typing import List, Dict, Any, Union, TypeVar

# standard libs
import json
import logging
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


__NT = type(None)
__VT = TypeVar('__VT', __NT, bool, int, float, str)
def __coerce_datetime(value: __VT) -> Union[__VT, datetime]:
    if not isinstance(value, str):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        return value


def __load_records(base: Base, path: str) -> List[Dict[str, Any]]:
    return [base(**{k: __coerce_datetime(v) for k, v in record.items()})
            for record in json.loads(assets.load_asset(path))]


# NOTE: order matters for foreign key references
__CORE_REFS = ['user', 'object_type', 'level', 'topic', ]
__TEST_REFS = ['facility', 'user', 'facility_map', 'client', 'session', 'object_type', 'level', 'topic', ]
__REFS = {'core': __CORE_REFS, 'test': __TEST_REFS}


def load_records(section: str) -> None:
    """Load stored record assets from `section`."""
    log.info(f'Loading {section} data')
    session = Session()
    for name in __REFS[section]:
        records = __load_records(tables[name], f'database/{section}/{name}.json')
        session.add_all(records)
        session.commit()
