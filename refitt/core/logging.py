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
Logging Configuration
=====================

REFITT uses the `logalpha` package for logging functionality. All messages
are written to <stderr> and should be redirected by their parent processes.

Levels
------
TRACE      Like DEBUG, but even more verbose for development or bug finding.
DEBUG      Low level notices (e.g., database connection).
STATUS     Like DEBUG, but allows progress tracking for repeated messages.
INFO       Informational messages of general interest.
EVENT      Like INFO, but tagged for easy tracking of milestones.
WARNING    Something unexpected or possibly problematic occurred.
ERROR      An error caused an action to not be completed.
CRITICAL   The entire application must halt.

Handlers
--------
STANDARD   Simple colorized console output. (no metadata)
DETAILED   Detailed (syslog-style) messages (with metadata)

Environment Variables
---------------------
REFITT_LOGGING_LEVEL      INT or NAME of logging level.
REFITT_LOGGING_HANDLER    STANDARD or DETAILED
"""

# type annotations
from __future__ import annotations
from typing import List, Callable

# standard libraries
import os
import io
import sys
import socket
from datetime import datetime
from dataclasses import dataclass

# external libraries
from logalpha import levels, colors, messages, handlers, loggers
from cmdkit.app import Application, exit_status

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

LEVELS_BY_NAME = {'TRACE': TRACE, 'DEBUG': DEBUG, 'STATUS': STATUS,
                  'INFO': INFO, 'EVENT': EVENT, 'WARNING': WARNING,
                  'ERROR': ERROR, 'CRITICAL': CRITICAL}


# NOTE: global handler list lets `Logger` instances aware of changes
#       to other logger's handlers. (i.e., changing from StandardHandler to DetailedHandler).
_handlers: List[handlers.Handler] = []


@dataclass
class Message(messages.Message):
    """Message data class (level, content, timestamp, topic, source, host)."""
    level: levels.Level
    content: str
    timestamp: datetime
    topic: str
    source: str = __appname__
    host: str = HOSTNAME


class Logger(loggers.Logger):
    """Logger for refitt."""

    levels = LEVELS
    colors = COLORS

    topic: str = __appname__
    Message: type = Message
    callbacks: dict = {'timestamp': datetime.now, }

    def __init__(self, topic: str) -> None:
        """Setup logger with custom callback for `topic`."""
        super().__init__()
        self.topic = topic
        self.callbacks = {**self.callbacks, 'topic': (lambda: topic)}

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
class StandardHandler(handlers.Handler):
    """Write basic colorized messages to standard error."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Colorize the log level and with only the message."""
        COLOR = Logger.colors[msg.level.value].foreground
        return f'{COLOR}{msg.level.name:<8}{RESET} {msg.content}'


@dataclass
class DetailedHandler(handlers.Handler):
    """Write detailed (syslog-like) messages to standard error."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Syslog style with padded spaces."""
        ts = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f'{ts} {msg.host} {msg.level.name:<8} [{msg.topic}] {msg.content}'


# persistent instances
STANDARD_HANDLER = StandardHandler(WARNING)
DETAILED_HANDLER = DetailedHandler(WARNING)
_handlers.append(STANDARD_HANDLER)


# derive initial logging level from environment
INITIAL_LEVEL = os.getenv('REFITT_LOGGING_LEVEL', 'WARNING')
try:
    INITIAL_LEVEL = LEVELS_BY_NAME[INITIAL_LEVEL]
except KeyError:
    try:
        INITIAL_LEVEL = LEVELS[int(INITIAL_LEVEL)]
    except (ValueError, IndexError):
        Logger(__name__).critical(f'unknown level: {INITIAL_LEVEL}')
        sys.exit(3)


HANDLERS_BY_NAME = {'STANDARD': STANDARD_HANDLER,
                    'DETAILED': DETAILED_HANDLER}

INITIAL_HANDLER = os.getenv('REFITT_LOGGING_HANDLER', 'STANDARD')
try:
    INITIAL_HANDLER = HANDLERS_BY_NAME[INITIAL_HANDLER]
except KeyError:
    Logger(__name__).critical(f'unknown handler: {INITIAL_HANDLER}')
    sys.exit(exit_status.runtime_error)


# set initial handler by environment variable or default
INITIAL_HANDLER.level = INITIAL_LEVEL
_handlers[0] = INITIAL_HANDLER


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
        _handlers[0].level = INITIAL_LEVEL
