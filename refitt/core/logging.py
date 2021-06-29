# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""
Logging configuration for REFITT

Enables custom logging format and level by configuration as well as streaming
messages to the database.
"""


# standard libs
import logging as _std

# internal libs
from .config import config

# logging attributes are extended by StreamKit as well as providing a handler
from streamkit.core import logging as _streamkit  # noqa: unused, but needs to execute
from streamkit.contrib.logging import StreamKitHandler

# public interface
__all__ = []


# isolate logging section from configuration
config = config.logging


# top-level loggers
refitt_logger = _std.getLogger('refitt')
refittd_logger = _std.getLogger('refittd')
refittctl_logger = _std.getLogger('refittctl')


# level set to logger (applies to all handlers)
refitt_logger.setLevel(getattr(_std, config.level.upper()))
refittd_logger.setLevel(getattr(_std, config.level.upper()))
refittctl_logger.setLevel(getattr(_std, config.level.upper()))


# enable streaming records to the database
stream_handler = None
if config.stream.enabled:
    stream_handler = StreamKitHandler(batchsize=config.stream.batchsize, timeout=config.stream.timeout)
    refitt_logger.addHandler(stream_handler)


# write to stderr
console_handler = _std.StreamHandler()
console_handler.setFormatter(_std.Formatter(config.format, datefmt=config.datefmt))
refitt_logger.addHandler(console_handler)
refittd_logger.addHandler(console_handler)
refittctl_logger.addHandler(console_handler)
