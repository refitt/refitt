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

# internal library
from ..__meta__ import __appname__


# get hostname from `socket` instead of `.config`
HOSTNAME = socket.gethostname()

# NOTICE messages won't actually be formatted with color.
LEVELS = levels.Level.from_names(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
COLORS = colors.Color.from_names(['blue', 'green', 'yellow', 'red', 'magenta'])
RESET = colors.Color.reset


# NOTE: global handler list lets `Logger.with_name` instances aware of changes
#       to other logger's handlers. (i.e., changing from SimpleConsoleHandler to ConsoleHandler).
_handlers = []


@dataclass
class Message(messages.Message):
    """A `logalpha.messages.Message` with a timestamp:`datetime` and source:`str`."""
    timestamp: datetime
    source: str


class Logger(loggers.Logger):
    """Logger for refitt."""

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
    debug: Callable[[str], None]
    info: Callable[[str], None]
    warning: Callable[[str], None]
    error: Callable[[str], None]
    critical: Callable[[str], None]


@dataclass
class ConsoleHandler(handlers.Handler):
    """Write messages to <stderr>."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Syslog style with padded spaces."""
        timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f'{timestamp} {HOSTNAME} {msg.source:<22} {msg.level.name:<8} {msg.content}'


@dataclass
class SimpleConsoleHandler(handlers.Handler):
    """Write shorter messages to <stderr> with color."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Colorize the log level and with only the message."""
        COLOR = Logger.colors[msg.level.value].foreground
        return f'{COLOR}{msg.level.name.lower():<8}{RESET} {msg.content}'


SYSLOG_HANDLER = ConsoleHandler(LEVELS[2])
SIMPLE_HANDLER = SimpleConsoleHandler(LEVELS[2])
_handlers.append(SIMPLE_HANDLER)

# inject logger back into cmdkit library
_cmdkit_logging.log = Logger()
