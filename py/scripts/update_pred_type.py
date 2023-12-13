#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Update predicted type for recommended objects."""


# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import sys
import functools

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# internal libs
from refitt.core.logging import Logger
from refitt.database.model import Model, Observation, Object, ObjectType
from refitt.database.connection import default_connection as db

# public interface
__all__ = []

# application logger
log = Logger.with_name('refitt')
Application.log_critical = log.critical
Application.log_exception = log.critical


PROGRAM = 'update-pred-type'
USAGE = f"""\
usage: {PROGRAM} [-h] ...
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-h, --help              Show this message and exit.\
"""


class UpdatePredTypeApp(Application):
    """Application class for prediction type updates."""

    interface = Interface(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS = True

    def run(self: UpdatePredTypeApp) -> None:
        """Run application."""

        log.info('Searching for model outputs')
        model_object_mapping = db.read.query(Model.id, Observation.object_id).join(Observation).all()
        log.info(f'Found {len(model_object_mapping)} existing models')

        object_groups = {}
        for (model_id, object_id), in zip(model_object_mapping):
            if object_id in object_groups:
                object_groups[object_id].append(model_id)
                log.debug(f'({object_id}) <- {model_id} ({len(object_groups[object_id])})')
            else:
                object_groups[object_id] = [model_id, ]
                log.debug(f'({object_id}) <- {model_id} ({len(object_groups[object_id])} total)')

        log.info(f'{len(object_groups)} distinct objects represented')
        for i, (object_id, model_ids) in enumerate(object_groups.items()):
            log.debug(f'Checking object {object_id} ({i+1}/{len(object_groups)})')
            model_id = max(model_ids)
            model = Model.from_id(model_id)
            pred_type = object_pred_type(model.data)
            if not pred_type:
                log.debug('Missing class information on model')
            elif not Object.from_id(object_id).pred_type:
                log.debug(f'Updating object ({object_id}: {pred_type["name"]})')
                Object.update(object_id, pred_type={'conv_auto_encoder': pred_type})
            else:
                log.debug(f'Ignoring object ({object_id}) with existing data')


def object_pred_type(data: dict) -> Optional[dict]:
    """Predicted object type name (e.g., {'name': 'Ia', 'score': 0.74})."""
    if 'class' not in data:
        return None
    types, *scores = data['class']
    obj_type = get_object_type(types[0])
    return {
        'id': obj_type.id,
        'name': obj_type.name,
        'score': round(float(scores[0]), 4),
    }


@functools.lru_cache(maxsize=None)
def get_object_type(name: str) -> ObjectType:
    """Fetch and cache `object_type.id` given `name`."""
    try:
        return ObjectType.from_name(name)
    except ObjectType.NotFound as exc:
        log.error(f'Object type not found ({name}) - trying again (with \'SN {name}\')')
        return ObjectType.from_name(f'SN {name}')


if __name__ == '__main__':
    sys.exit(UpdatePredTypeApp.main(sys.argv[1:]))
