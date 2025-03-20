# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database interface, models, and methods."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Any, Type, Final

# standard libs
import json

# external libs
from sqlalchemy.engine import Engine

# internal libs
from refitt import assets
from refitt.core.logging import Logger
from refitt.database.connection import ConnectionManager, default_connection as db
from refitt.database.model import Entity, tables

# public interface
__all__ = ['get_engine', 'get_provider', 'create_all', 'drop_all', 'load_defaults', ]

# module logger
log = Logger.with_name(__name__)


def get_engine(scope: str = 'write') -> Engine:
    """Retrieve underlying engine for given session scope."""
    return db.get_engine(db.name_from_scope(scope))


def get_provider(scope: str = 'write') -> str:
    """Get configured provider for given session scope."""
    return db.get_config(db.name_from_scope(scope)).provider


def create_all(scope: str = 'write') -> None:
    """Create all database objects."""
    log.info(f'Creating all database objects ({scope})')
    Entity.metadata.create_all(get_engine(scope))


def drop_all(scope: str = 'write') -> None:
    """Drop all database objects."""
    log.info(f'Dropping all database objects: {scope}')
    Entity.metadata.drop_all(get_engine(scope))


def load_records(interface: Type[Entity], path: str) -> List[Dict[str, Any]]:
    """Load all records from JSON file `path` into model of type `interface`."""
    return [interface.from_json(record) for record in json.loads(assets.load_asset(path))]


# NOTE: order matters for foreign key references
ENTITIES: Final[Dict[str, List[str]]] = {
    'core': ['user', 'object_type', 'model_type', 'level', 'topic', ],
    'test': ['facility', 'user', 'facility_map', 'client', 'session',
             'object_type', 'object', 'source_type', 'source',
             'epoch', 'observation_type', 'observation', 'model_type', 'model', 'alert', 'file_type', 'file',
             'recommendation_tag', 'recommendation', 'level', 'topic', ]
}


def load_defaults(scope: str, test: bool = False) -> None:
    """Load stored default records into database."""
    role = 'core' if test is False else 'test'
    log.info(f'Loading default records ({role})')
    session = db.get_session(db.name_from_scope(scope))
    for name in ENTITIES[role]:
        records = load_records(tables[name], f'database/{role}/{name}.json')
        session.add_all(records)
        session.commit()
