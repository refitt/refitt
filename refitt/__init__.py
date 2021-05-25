# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

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
