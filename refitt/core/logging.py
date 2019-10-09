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

# standard libraries
import io
import sys
from datetime import datetime
from dataclasses import dataclass

# external libraries
from logalpha import levels, colors, messages, handlers, loggers
from cmdkit import logging as _cmdkit_logging

# internal library
from ..__meta__ import __appname__
from ..core.config import HOSTNAME

# NOTICE messages won't actually be formatted with color.
LEVELS = levels.Level.from_names(['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL'])
COLORS = colors.Color.from_names(['blue', 'green', 'white', 'yellow', 'red', 'magenta'])
RESET = colors.Color.reset


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


    def with_name(self, name: str) -> 'Logger':
        """Inject alternate `name` into callbacks."""
        logger = self.__class__()
        logger.callbacks = {**logger.callbacks, 'source': (lambda: name)}
        logger.handlers = self.handlers[:]  # same handler instances
        return logger


    # FIXME: explicitly named aliases to satisfy pylint;
    #        these levels are already available but pylint complains


    def debug(self, *args, **kwargs) -> None:
        return self.write(loggers.Logger.levels[0], *args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        return self.write(loggers.Logger.levels[1], *args, **kwargs)

    def warning(self, *args, **kwargs) -> None:
        return self.write(loggers.Logger.levels[2], *args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        return self.write(loggers.Logger.levels[3], *args, **kwargs)

    def critical(self, *args, **kwargs) -> None:
        return self.write(loggers.Logger.levels[4], *args, **kwargs)


@dataclass
class ConsoleHandler(handlers.Handler):
    """Write messages to <stderr>."""

    level: levels.Level
    resource: io.TextIOWrapper = sys.stderr

    def format(self, msg: Message) -> str:
        """Syslog style with padded spaces."""
        timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return f'{timestamp} {HOSTNAME:<30} {msg.source:<22} {msg.level.name:<8} {msg.content}'



HANDLER = ConsoleHandler(LEVELS[1])

logger = Logger()
logger.handlers.append(HANDLER)

# inject logger back into cmdkit library
_cmdkit_logging.log = logger
