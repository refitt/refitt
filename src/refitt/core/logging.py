# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Logging configuration."""


# type annotations
from __future__ import annotations
from typing import Dict, Any

# standard libraries
import sys
import uuid
import socket
import logging

# external libs
from cmdkit.app import exit_status
from cmdkit.config import ConfigurationError
from streamkit.contrib.logging import StreamKitHandler

# internal libs
from refitt.core.ansi import Ansi
from refitt.core.config import config, blame
from refitt.core.exceptions import write_traceback

# public interface
__all__ = ['Logger', 'StreamHandler', 'StreamKitHandler', 'HOSTNAME', 'INSTANCE', ]


# Cached for later use
HOSTNAME = socket.gethostname()


# Unique for every instance of refitt
INSTANCE = str(uuid.uuid4())


# Canonical colors for logging messages
level_color: Dict[str, Ansi] = {
    'NULL': Ansi.NULL,
    'TRACE': Ansi.CYAN,
    'DEBUG': Ansi.BLUE,
    'INFO': Ansi.GREEN,
    'WARNING': Ansi.YELLOW,
    'ERROR': Ansi.RED,
    'CRITICAL': Ansi.MAGENTA
}


TRACE: int = logging.DEBUG - 5
logging.addLevelName(TRACE, 'TRACE')


class Logger(logging.Logger):
    """Extend Logger to implement TRACE level."""

    def trace(self, msg: str, *args, **kwargs):
        """Log 'msg % args' with severity 'TRACE'."""
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    @classmethod
    def with_name(cls: Logger, name: str) -> Logger:
        """Shorthand for `log: Logger = logging.getLogger(name)`."""
        return logging.getLogger(name)


# Inject class back into logging library
logging.setLoggerClass(Logger)


class LogRecord(logging.LogRecord):
    """Extends LogRecord to include the hostname and ANSI color codes."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.app_id = INSTANCE
        self.hostname = HOSTNAME
        self.ansi_level = level_color.get(self.levelname, Ansi.NULL).value
        self.ansi_reset = Ansi.RESET.value
        self.ansi_bold = Ansi.BOLD.value
        self.ansi_faint = Ansi.FAINT.value
        self.ansi_italic = Ansi.ITALIC.value
        self.ansi_underline = Ansi.UNDERLINE.value
        self.ansi_black = Ansi.BLACK.value
        self.ansi_red = Ansi.RED.value
        self.ansi_green = Ansi.GREEN.value
        self.ansi_yellow = Ansi.YELLOW.value
        self.ansi_blue = Ansi.BLUE.value
        self.ansi_magenta = Ansi.MAGENTA.value
        self.ansi_cyan = Ansi.CYAN.value
        self.ansi_white = Ansi.WHITE.value


# Inject factory back into logging library
logging.setLogRecordFactory(LogRecord)


class StreamHandler(logging.StreamHandler):
    """A StreamHandler that panics on exceptions in the logging configuration."""

    def handleError(self, record: LogRecord) -> None:
        """Pretty-print message and write traceback to file."""
        err_type, err_val, tb = sys.exc_info()
        write_traceback(err_val, module=__name__)
        sys.exit(exit_status.bad_config)


def level_from_name(name: Any, source: str = 'logging.level') -> int:
    """Get level value from `name`."""
    label = blame(config, *source.split('.'))
    if not isinstance(name, str):
        raise ConfigurationError(f'Expected string for logging level, given \'{name}\' ({label})')
    name = name.upper()
    if name == 'TRACE':
        return TRACE
    elif name in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        return getattr(logging, name)
    else:
        raise ConfigurationError(f'Unsupported logging level \'{name}\' ({label})')


try:
    levelname = config.logging.level
    level = level_from_name(levelname)
except Exception as error:
    write_traceback(error, module=__name__)
    sys.exit(exit_status.bad_config)


try:
    handler = StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(config.logging.format,
                          datefmt=config.logging.datefmt)
    )
except Exception as error:
    write_traceback(error, module=__name__)
    sys.exit(exit_status.bad_config)


refitt_logger = logging.getLogger('refitt')
refittd_logger = logging.getLogger('refittd')
refittctl_logger = logging.getLogger('refittctl')


refitt_logger.setLevel(level)
refittd_logger.setLevel(level)
refittctl_logger.setLevel(level)


refitt_logger.addHandler(handler)
refittd_logger.addHandler(handler)
refittctl_logger.addHandler(handler)


stream_handler = None
try:
    if config.logging.stream.enabled:
        stream_handler = StreamKitHandler(batchsize=config.stream.batchsize, timeout=config.stream.timeout)
        refitt_logger.addHandler(stream_handler)
        refittd_logger.addHandler(stream_handler)
        refittctl_logger.addHandler(stream_handler)
except Exception as error:
    write_traceback(error, module=__name__)
    sys.exit(exit_status.bad_config)
