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
from ...core.apps import Application
from ...core.parser import ArgumentParser
from ...core.logging import get_logger
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# program name is constructed from module file name
NAME = os.path.basename(__file__).strip('.py').replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <input-file> [-o <output-file>]
       {PADDING} [--debug | --logging LEVEL]
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
<input-file> PATH      Path to candidates file.

options:
-h, --help             Show this message and exit.
-o, --output PATH      Path for output file.

{EPILOG}
"""

# initialize module level logger
log = get_logger(NAME)


class PipelineApp(Application):

    interface = ArgumentParser(PROGRAM, USAGE, HELP)
    ALLOW_NOARGS: bool = True

    def run(self) -> None:
        """Run Refitt pipeline."""
        log.info('starting pipeline')


# inherit docstring from module
PipelineApp.__doc__ = __doc__
