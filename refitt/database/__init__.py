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
from typing import List, Dict, Any

# standard libs
import json
import logging

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


def _load_records(base: Base, path: str) -> List[Dict[str, Any]]:
    return [base(**record) for record in json.loads(assets.load_asset(path))]


CORE_REFS = ['user', 'level', 'topic', ]
def load_coredata() -> None:
    """Load core dataset records into the database."""
    log.info('Loading core data')
    session = Session()
    for name in CORE_REFS:
        session.add_all(_load_records(tables[name], f'database/core/{name}.json'))
        session.commit()


# NOTE: order matters for foreign key references
TEST_REFS = ['facility', 'user', 'facility_map', 'client', 'session', ]
def load_testdata() -> None:
    """Load test dataset records into the database."""
    log.info('Loading test data')
    session = Session()
    for name in TEST_REFS:
        session.add_all(_load_records(tables[name], f'database/test/{name}.json'))
        session.commit()
