#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Resolve next batch of Type IIP objects for modeling."""


# type annotations
from __future__ import annotations
from typing import List, Set, Optional, Type

# standard libs
import os
import sys
import json
from datetime import datetime, timedelta

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface
from sqlalchemy import func

# internal libs
from refitt.core.platform import default_path
from refitt.core.logging import Logger
from refitt.data.tns.catalog import TNSCatalog
from refitt.database.model import Model, ModelType, Observation, Object, Source, Epoch, SourceType
from refitt.database.interface import Session

# public interface
__all__ = []

# application logger
log = Logger.with_name('refitt')
Application.log_critical = log.critical
Application.log_exception = log.critical


PROGRAM = 'pull_type_iip'
USAGE = f"""\
usage: {PROGRAM} [-h] [-f] [--limit NUM] [--filter-epoch NUM]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-f, --ignore-cache         Force re-processing of TNS catalog.
-l, --limit          NUM   Limit number of returned objects (default: 50).
-e, --filter-epoch   NUM   Number of previous epochs to filter out.
-h, --help                 Show this message and exit.\
"""


class PullTypeIIPApp(Application):
    """Resolve next batch of Type IIP objects for modeling."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    allow_cache: bool = True
    interface.add_argument('-f', '--ignore-cache', action='store_false', dest='allow_cache')

    limit: int = 50
    interface.add_argument('-l', '--limit', type=int, default=limit)

    filter_epoch: int = 1
    interface.add_argument('-e', '--filter-epoch', type=int, default=filter_epoch)

    def run(self: PullTypeIIPApp) -> None:
        """Run application."""
        objects = self.load_objects(cache=self.allow_cache)
        objects = self.sort_by_count(objects)
        objects = self.filter_previous(objects)
        self.print_info(objects)

    def print_info(self: PullTypeIIPApp, objects: List[Object]) -> None:
        """Show identifier and redshift if available."""
        log.info(f'Including {len(objects[:self.limit])} objects')
        for object in objects[:self.limit]:
            redshift = object.data.get('tns', {}).get('redshift', None)
            if redshift and redshift != 'None':
                print(f'{object.aliases["ztf"]}  {object.data["tns"]["redshift"]:.3f}')
            else:
                print(f'{object.aliases["ztf"]}  -')

    def filter_previous(self: PullTypeIIPApp, objects: List[Object]) -> List[Object]:
        """Filter out any objects represented in recent epochs."""
        return [
            object for object in objects
            if object.id not in self.previous_objects(num_epochs=self.filter_epoch)
        ]

    @staticmethod
    def previous_objects(num_epochs: int = 1) -> Set[int]:
        """Query database for objects already forecasted in previous epochs."""
        return set([
            object_id
            for model_id, object_id in
            Session.query(Model.id, Observation.object_id)
                .join(Observation, Model.observation_id == Observation.id)
                .filter(Model.epoch_id >= Epoch.latest().id - num_epochs)
                .filter(Model.type_id == ModelType.from_name('core_collapse_inference').id)
        ])

    @staticmethod
    def sort_by_count(objects: List[Object], limit: int = 200) -> List[Object]:
        """
        Query database for given objects aggregated by
        number of observations for that object, in ascending order of count.
        Only objects found in database will be returned.
        """
        return [
            Object.from_id(object_id)
            for object_id, count in
            Session.query(Observation.object_id, func.count(Observation.object_id))
                .join(Source, Observation.source_id == Source.id)
                .filter(Observation.object_id.in_([object.id for object in objects]))
                .filter(Source.type_id.notin_([SourceType.from_name('synthetic').id, ]))
                .group_by(Observation.object_id)
                .order_by(func.count(Observation.object_id))
                .limit(limit)
        ]

    CACHE_PATH = os.path.join(default_path.lib, 'tns', 'objects_type_iip.json')
    EXPIRED_AFTER = timedelta(days=1)

    def load_objects(self: PullTypeIIPApp, cache: bool = True,
                     expired_after: timedelta = EXPIRED_AFTER) -> List[Object]:
        """Process names from TNS or load from cache if available."""
        if cache and self.check_cache_valid(expired_after):
            return self.load_from_cache()
        else:
            return self.load_from_tns(cache=cache)

    @classmethod
    def load_from_tns(cls: Type[PullTypeIIPApp], cache: bool = True) -> List[Object]:
        """Pull TNS catalog down from the web and filter for type IIP objects."""
        tns = TNSCatalog.from_web()
        names = cls.filter_names_by_type(tns)
        log.info(f'Found {len(names)} type IIP objects')
        objects = [cls.get_object(tns, name) for name in names]
        objects = [object for object in objects if object is not None]
        log.info(f'Identified {len(objects)} objects in database')
        if cache:
            cls.write_cache(objects)
        return objects

    @classmethod
    def write_cache(cls: Type[PullTypeIIPApp], objects: List[Object]) -> None:
        """Write existing list of object records to cache."""
        log.info(f'Writing {len(objects)} to cache ({cls.CACHE_PATH})')
        with open(cls.CACHE_PATH, mode='w') as stream:
            json.dump([object.to_json() for object in objects], stream)

    @classmethod
    def load_from_cache(cls: Type[PullTypeIIPApp]) -> List[Object]:
        """Load names from file."""
        log.info(f'Loading from cache ({cls.CACHE_PATH})')
        with open(cls.CACHE_PATH, mode='r') as stream:
            return [Object.from_json(record) for record in json.load(stream)]

    @classmethod
    def check_cache_valid(cls, expired_after: timedelta) -> bool:
        """Check cache file is expired or missing."""
        if not os.path.exists(cls.CACHE_PATH):
            log.debug(f'Cache not found ({cls.CACHE_PATH})')
            return False
        age = datetime.now() - datetime.fromtimestamp(os.stat(cls.CACHE_PATH).st_mtime)
        if age > expired_after:
            log.debug(f'Cache expired ({age} > {expired_after})')
            return False
        else:
            return True

    @staticmethod
    def filter_names_by_type(tns: TNSCatalog) -> List[str]:
        """Return list of IAU names with type IIP."""
        return list(tns.data.loc[tns.data.type == 'SN IIP'].name)

    @staticmethod
    def get_object(tns: TNSCatalog, iau_name: str) -> Optional[Object]:
        """Load object by some internal name within TNS."""
        record = tns.data.loc[tns.data.name == iau_name].iloc[0]
        names = [name.strip() for name in record.internal_names.strip().split(',')]
        for name in [iau_name, *names]:
            if name:  # NOTE: possible '' blank result
                log.debug(f'Checking object ({name})')
                try:
                    object = Object.from_name(name)
                    log.debug(f'Identified object ({object.id}: {name})')
                    return object
                except Object.NotFound:
                    pass
        else:
            log.error(f'Failed to identify object ({iau_name})')
            return None


if __name__ == '__main__':
    sys.exit(PullTypeIIPApp.main(sys.argv[1:]))
