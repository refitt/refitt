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
The Recommender Engine for Intelligent Transient Tracking.

This package provides access to the library of applications, tools, and
services within the REFITT system.
"""


from .__meta__ import (__appname__, __version__, __authors__, __contact__, __license__,
                       __copyright__, __description__)


# NOTE: forced logging import triggers configuration and logging setup
from .core.config import config
from .core import logging


# NOTE: render uncaught exceptions with highlighting
import sys
if sys.stdout.isatty():
    from rich.traceback import install
    install()
