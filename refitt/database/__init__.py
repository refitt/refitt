# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database interface, models, and methods."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Any, Type

# standard libs
import json
import logging

# internal libs
from .. import assets
from .core import engine, Session, config
from .model import Base, tables

# public interface
__all__ = ['init_database', 'drop_database', 'load_records', ]


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


def __load_records(base: Type[Base], path: str) -> List[Dict[str, Any]]:
    """Load all records from JSON file `path` into model of type `base`."""
    return [base.from_json(record) for record in json.loads(assets.load_asset(path))]


# NOTE: order matters for foreign key references
__REFS: Dict[str, List[str]] = {
    'core': ['user', 'object_type', 'level', 'topic', ],
    'test': ['facility', 'user', 'facility_map', 'client', 'session', 'object_type', 'object', 'source_type',
             'source', 'observation_type', 'observation', 'forecast', 'alert', 'file_type', 'file',
             'recommendation_group', 'recommendation_tag', 'recommendation', 'level', 'topic', ]
}

def load_records(section: str) -> None:
    """Load stored record assets from `section` into database."""
    log.info(f'Loading {section} data')
    session = Session()
    for name in __REFS[section]:
        records = __load_records(tables[name], f'database/{section}/{name}.json')
        session.add_all(records)
        session.commit()
