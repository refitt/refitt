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

"""
Logging configuration.

REFITT uses the `logalpha` package for logging functionality. All messages
are written to <stderr> and should be redirected by their parent processes.

Levels
------
TRACE      Like DEBUG, but even more verbose for development or bug finding
DEBUG      Low level notices (e.g., database connection)
STATUS     Like DEBUG, but allows progress tracking
INFO       General messages
EVENT      Like INFO, but tagged for easy tracking of milestones
WARNING
ERROR
CRITICAL

Handlers
--------
STANDARD   Simple colorized console output. (no metadata)
SYSLOG     Detailed (syslog-style) messages (with metadata)
"""

# type annotations
from __future__ import annotations
from typing import List, Callable

# standard libraries
import io
import sys
import socket
from datetime import datetime
from dataclasses import dataclass

# external libraries
from logalpha import levels, colors, messages, handlers, loggers
from cmdkit import logging as _cmdkit_logging
from cmdkit.app import Application

# internal library
from ..__meta__ import __appname__


# get hostname from `socket` instead of `.config`
HOSTNAME = socket.gethostname()


# logging levels associated with integer value and color codes
LEVELS = levels.Level.from_names(('TRACE', 'DEBUG', 'STATUS', 'INFO', 'EVENT', 'WARNING', 'ERROR', 'CRITICAL'))
COLORS = colors.Color.from_names(('blue', 'blue', 'blue', 'green', 'green', 'yellow', 'red', 'magenta'))
RESET = colors.Color.reset


# named logging levels
TRACE    = LEVELS[0]
DEBUG    = LEVELS[1]
STATUS   = LEVELS[2]
INFO     = LEVELS[3]
EVENT    = LEVELS[4]
WARNING  = LEVELS[5]
ERROR    = LEVELS[6]
CRITICAL = LEVELS[7]


# NOTE: global handler list lets `Logger.with_name` instances aware of changes
#       to other logger's handlers. (i.e., changing from SimpleConsoleHandler to ConsoleHandler).
_handlers: List[handlers.Handler] = []


@dataclass
class Message(messages.Message):
    """A `logalpha.messages.Message` with a timestamp:`datetime` and source:`str`."""
    timestamp: datetime
    source: str


class Logger(loggers.Logger):
    """Logger for refitt."""

    levels = LEVELS
    colors = COLORS

    Message: type = Message
    callbacks: dict = {'timestamp': datetime.now,
                       'source': (lambda: __appname__)}

    @classmethod
    def with_name(cls, name: str) -> Logger:
        """Inject alternate `name` into callbacks."""
        self = cls()
        self.callbacks = {**self.callbacks, 'source': (lambda: name)}
        return self

    @property
    def handlers(self) -> List[handlers.Handler]:
        """Override of local handlers to global list."""
        global _handlers
        return _handlers

    # FIXME: explicitly named aliases to satisfy pylint;
    #        these levels are already available but pylint complains
    trace: Callable[[str], None]
    debug: Callable[[str], None]
    status: Callable[[str], None]
    info: Callable[[str], None]
    event: Callable[[str], None]
    warning: Callable[[str], None]
    error: Callable[[str], None]
    critical: Callable[[str], None]


@dataclass
class SimpleHandler(handlers.Handler):
    """Write detailed messages to standard error."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Colorize the log level and with only the message."""
        COLOR = Logger.colors[msg.level.value].foreground
        timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f'{COLOR}[{timestamp}] {msg.content}{RESET}'


@dataclass
class DetailedHandler(handlers.Handler):
    """Write simple colorized messages to standard error."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Syslog style with padded spaces."""
        timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f'{timestamp} {HOSTNAME} {msg.source:<22} {msg.level.name:<8} {msg.content}'


# persistent instances
SIMPLE_HANDLER = SimpleHandler(WARNING)
DETAILED_HANDLER = DetailedHandler(WARNING)


# always start with the simple handler
_handlers.append(SIMPLE_HANDLER)


# inject logger back into cmdkit library
_cmdkit_logging.log = Logger()
Application.log_error = _cmdkit_logging.log.critical


# NOTE: All of the command line entry-points call this function
#       to setup their logging interface.
def cli_setup(app: Application) -> None:
    """Swap out handler for `DETAILED_HANDLER` and set level."""
    if app.syslog:  # noqa (missing from base class)
        _handlers[0] = DETAILED_HANDLER
    if app.debug:  # noqa (missing from base class)
        _handlers[0].level = DEBUG
    elif app.verbose:  # noqa (missing from base class)
        _handlers[0].level = INFO
    else:
        _handlers[0].level = WARNING
