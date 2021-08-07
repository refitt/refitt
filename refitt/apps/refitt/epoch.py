# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Manage epochs."""


# type annotations
from __future__ import annotations

import json
from typing import IO, Dict, Callable

# standard libs
import os
import sys
import logging
from functools import cached_property

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
from rich.console import Console
from rich.syntax import Syntax

# internal libs
from ...database.model import Epoch
from ...core.exceptions import log_exception

# public interface
__all__ = ['EpochApp', ]


PROGRAM = 'refitt epoch'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} [-h] (new [--print] | latest [--json | --id])
{__doc__}\
"""

HELP = f"""\
{USAGE}

action:
latest           Request most recent epoch.
new              Create new epoch (cannot be undone).
    
options:
    --print      Write new epoch ID to stdout.
    --json       Write output in JSON format.
    --id         Only write ID as output.
-h, --help       Show this message and exit.\
"""


class EpochApp(Application):
    """Application class for managing epochs."""

    interface = Interface(PROGRAM, USAGE, HELP)

    action: str
    interface.add_argument('action', choices=['new', 'latest'])

    show_id: bool
    show_json: bool
    view_interface = interface.add_mutually_exclusive_group()
    view_interface.add_argument('--id', action='store_true', dest='show_id')
    view_interface.add_argument('--json', action='store_true', dest='show_json')

    verbose: bool
    interface.add_argument('--print', action='store_true', dest='verbose')

    def run(self) -> None:
        """Run action."""
        self.actions[self.action]()

    @cached_property
    def actions(self) -> Dict[str, Callable[[], None]]:
        """Map of names to action callbacks."""
        return {
            'new': self.create_epoch,
            'latest': self.show_latest,
        }

    def create_epoch(self) -> None:
        """Create new epoch and print new epoch ID."""
        if self.show_id or self.show_json:
            raise ArgumentError('Cannot use --id/--json for \'new\'')
        epoch = Epoch.new()
        if self.verbose:
            print(epoch.id)

    def show_latest(self) -> None:
        """Query for latest epoch and print epoch ID."""
        if self.verbose:
            raise ArgumentError('Use of --print for \'latest\' is redundant')
        epoch = Epoch.latest()
        if self.show_id:
            print(epoch.id)
        elif self.show_json:
            content = json.dumps(epoch.to_json())
            if sys.stdout.isatty():
                Console().print(Syntax(content, 'json',
                                       word_wrap=True, theme='solarized-dark',
                                       background_color='default'))
            else:
                print(content)
        else:
            print(f'Epoch {epoch.id} ({epoch.created})')
