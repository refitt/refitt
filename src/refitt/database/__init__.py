# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database interface, models, and methods."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Any, Type

# standard libs
import json
import logging

# external libs
from sqlalchemy.engine import Engine

# internal libs
from .. import assets
from .interface import engine as __engine, Session, config
from .model import ModelInterface, tables

# public interface
__all__ = ['create_all', 'drop_all', 'load_all', 'config', ]


# initialize module level logger
log = logging.getLogger(__name__)


def create_all(base: Type[ModelInterface] = ModelInterface, engine: Engine = __engine) -> None:
    """Create all database objects."""
    log.info('Creating all database objects')
    base.metadata.create_all(engine)


def drop_all(base: Type[ModelInterface] = ModelInterface, engine: Engine = __engine) -> None:
    """Drop all database objects."""
    log.warning('Dropping all database objects')
    base.metadata.drop_all(engine)


def __load_records(base: Type[ModelInterface], path: str) -> List[Dict[str, Any]]:
    """Load all records from JSON file `path` into model of type `base`."""
    return [base.from_json(record) for record in json.loads(assets.load_asset(path))]


# NOTE: order matters for foreign key references
__REFS: Dict[str, List[str]] = {
    'core': ['user', 'object_type', 'model_type', 'level', 'topic', ],
    'test': ['facility', 'user', 'facility_map', 'client', 'session',
             'object_type', 'object', 'source_type', 'source',
             'epoch', 'observation_type', 'observation', 'model_type', 'model', 'alert', 'file_type', 'file',
             'recommendation_tag', 'recommendation', 'level', 'topic', ]
}


def load_all(role: str) -> None:
    """Load stored record assets from `role` into database."""
    log.info(f'Loading {role} data')
    session = Session()
    for name in __REFS[role]:
        records = __load_records(tables[name], f'database/{role}/{name}.json')
        session.add_all(records)
        session.commit()
