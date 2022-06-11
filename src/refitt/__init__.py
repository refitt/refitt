# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""
The Recommender Engine for Intelligent Transient Tracking.

This package provides access to the library of applications, tools, and
services within the REFITT system.
"""


# standard libs
import sys

# external libs
from rich.traceback import install as enable_rich_tracebacks

# internal libs (forced initialization)
from refitt.core.config import config
from refitt.core import logging

# public interface
__all__ = ['__appname__', '__version__', '__authors__', '__developer__', '__contact__',
           '__license__', '__website__', '__copyright__', '__description__',
           '__keywords__', '__ascii_art__', ]

# project metadata
__appname__     = 'refitt'
__version__     = '0.24.0'
__authors__     = ['Dan Milisavljevic <dmilisav@purdue.edu>',
                   'Niharika Sravan <nsravan@purdue.edu>',
                   'Geoffrey Lentner <glentner@purdue.edu>',
                   'Mark Linvill <mlinvill@purdue.edu>',
                   'Bhagya Subrayan <bsubraya@purdue.edu>',
                   'Katie Weil <keweil@purdue.edu>',
                   'Josh Church <church10@purdue.edu>',
                   'John Banovetz <jbanovet@purdue.edu>',
                   ]
__developer__   = 'Geoffrey Lentner'
__contact__     = 'glentner@purdue.edu'
__license__     = 'Apache License 2.0'
__website__     = 'https://github.com/refitt/refitt'
__copyright__   = 'REFITT Team 2019-2022'
__description__ = 'The Recommender Engine for Intelligent Transient Tracking.'
__keywords__    = 'astronomy science machine-learning recommendation service'
__ascii_art__   = r"""
    ____  ____________________________
   / __ \/ ____/ ____/  _/_  __/_  __/
  / /_/ / __/ / /_   / /  / /   / /
 / _, _/ /___/ __/ _/ /  / /   / /
/_/ |_/_____/_/   /___/ /_/   /_/
"""


# Enable rich tracebacks for interactive shells
if sys.stdout.isatty() and hasattr(sys, 'ps1'):
    enable_rich_tracebacks()
