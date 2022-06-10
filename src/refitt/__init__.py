# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""
The Recommender Engine for Intelligent Transient Tracking.

This package provides access to the library of applications, tools, and
services within the REFITT system.
"""


# standard libs
import sys

# NOTE: forced logging import triggers configuration and logging setup
from .core.config import config
from .core import logging
from .__meta__ import (__appname__, __version__, __authors__, __contact__, __license__,
                       __copyright__, __description__)

# external libs
from rich.traceback import install as enable_rich_tracebacks


if sys.stdout.isatty() and hasattr(sys, 'ps1'):
    enable_rich_tracebacks()
