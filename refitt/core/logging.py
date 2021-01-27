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


# isolate logging section from configuration
config = config.logging


# base logger
refitt_logger = _std.getLogger('refitt')
refitt_logger.setLevel(getattr(_std, config.level.upper()))


# enable streaming records to the database
stream_handler = None
if config.stream.enabled:
    stream_handler = StreamKitHandler(batchsize=config.stream.batchsize, timeout=config.stream.timeout)
    refitt_logger.addHandler(stream_handler)


# log messages to stderr
console_handler = _std.StreamHandler()
console_handler.setFormatter(_std.Formatter(config.format, datefmt=config.datefmt))
refitt_logger.addHandler(console_handler)
