# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Publish existing forecast outputs."""


# type annotations
from __future__ import annotations
from typing import List, IO

# standard libs
import os
import sys
from datetime import datetime
from functools import partial, cached_property

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from sqlalchemy.exc import IntegrityError

# internal libs
from refitt.core.exceptions import handle_exception
from refitt.core.logging import Logger
from refitt.core.schema import SchemaError
from refitt.forecast import load_model
from refitt.forecast.model import ModelData
from refitt.database.model import Object

# public interface
__all__ = ['ForecastPublishApp', ]

# application logger
log = Logger.with_name('refitt')


PROGRAM = 'refitt forecast publish'
USAGE = f"""\
usage: {PROGRAM} FILE [FILE...] [--observation-id ID | --primary FILE] [--print]
{__doc__}\
"""

HELP = f"""\
{USAGE}

arguments:
FILE                  Path to JSON file(s).

options:
    --print           Print ID of published model(s). 
-h, --help            Show this message and exit.\
"""


class ForecastPublishApp(Application):
    """Application class for forecast model data publishing."""

    interface = Interface(PROGRAM, USAGE, HELP)

    sources: List[str]
    interface.add_argument('sources', nargs='*')

    primary_filepath: str = None
    observation_id: int = None
    primary_interface = interface.add_mutually_exclusive_group()
    primary_interface.add_argument('-p', '--primary', default=None, dest='primary_filepath')
    primary_interface.add_argument('-i', '--observation-id', type=int)

    epoch_id: int = None
    interface.add_argument('-e', '--epoch-id', type=int, default=None)

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    exceptions = {
        IntegrityError: partial(handle_exception, logger=log,
                                status=exit_status.runtime_error),
        SchemaError: partial(handle_exception, logger=log,
                             status=exit_status.runtime_error),
        RuntimeError: partial(handle_exception, logger=log,
                              status=exit_status.runtime_error),
        ModelData.Error: partial(handle_exception, logger=log,
                                 status=exit_status.runtime_error),
        **Application.exceptions,
    }

    def run(self) -> None:
        """Business logic of command."""
        self.check_args()
        self.check_sources()
        if self.observation_id:
            models = [self.load(source) for source in self.sources]
        else:
            primary_model = self.load(self.primary_filepath)
            self.observation_id = primary_model.publish_observation(epoch_id=self.epoch_id).id
            models = [primary_model, ] + [self.load(source) for source in self.sources]
        self.publish(*models)
        self.update_object(*models)

    def check_args(self) -> None:
        """Ensure at least --observation-id or --primary."""
        if self.primary_filepath and self.observation_id:
            raise ArgumentError('Cannot provide both --primary and --observation-id')
        if not self.primary_filepath and not self.observation_id:
            raise ArgumentError('Must specify either --primary or --observation-id')

    def check_sources(self) -> None:
        """Validate provided file paths."""
        if '-' in self.sources and len(self.sources) > 1:
            raise ArgumentError('Cannot load from <stdin> with multiple sources')
        if '-' not in self.sources:
            for filepath in self.sources:
                if not os.path.exists(filepath):
                    raise RuntimeError(f'File not found: {filepath}')
                if not os.path.isfile(filepath):
                    raise RuntimeError(f'Not a file: {filepath}')
        if self.primary_filepath:
            if not os.path.exists(self.primary_filepath):
                raise RuntimeError(f'File not found: {self.primary_filepath}')
            if not os.path.isfile(self.primary_filepath):
                raise RuntimeError(f'Not a file: {self.primary_filepath}')
            if self.primary_filepath in self.sources:
                primary_index = self.sources.index(self.primary_filepath)
                self.sources.pop(primary_index)
        self.sources = list(set(self.sources))
        if not self.primary_filepath and not self.sources:
            raise ArgumentError('No sources given')

    def publish(self, *models: ModelData) -> None:
        """Publish a loaded model."""
        for model in models:
            self.write(model.publish(observation_id=self.observation_id, epoch_id=self.epoch_id).id)

    @staticmethod
    def update_object(*models: ModelData) -> None:
        """Update object with predicted types from models."""
        obj_id = models[0].object_id
        obj = Object.from_id(obj_id)
        pred_type = {model.name: model.object_pred_type for model in models if model.object_pred_type}
        pred_type = {**obj.pred_type, **pred_type}  # retain previous if any exist
        if obj.pred_type != pred_type:
            Object.update(obj_id, pred_type=pred_type,
                          history={**obj.history, str(datetime.now().astimezone()): obj.pred_type})

    @staticmethod
    def load(filepath: str) -> ModelData:
        """Load model data."""
        return load_model(filepath if filepath != '-' else sys.stdin)

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)
