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

"""End-to-end workflow for refitt."""

# standard libs
import os

# internal libs
from ...core.logging import logger
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface


# program name is constructed from module file name
NAME = os.path.basename(__file__).strip('.py').replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <source> [--output-directory PATH]
       {PADDING} [--debug | --logging LEVEL] [--simple-logging]
       {PADDING} [--help] [--version]

{__doc__}\
"""

EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""

HELP = f"""\
{USAGE}

arguments:
<source>                       Path to candidates file.

options:
-o, --output-directory  PATH   Directory for output files.
-h, --help                     Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = logger.with_name(f'{__appname__}.{NAME}')


class PipelineApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    # input file containing list of candidates/alerts
    source: str = '-'
    interface.add_argument('source')

    def run(self) -> None:
        """Run Refitt pipeline."""
        log.info('starting pipeline')


# inherit docstring from module
PipelineApp.__doc__ = __doc__
