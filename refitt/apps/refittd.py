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

"""The refitt daemon service."""

# internal libs
from ..core.apps import Application
from ..core.parser import ArgumentParser
from ..core.logging import get_logger
from ..__meta__ import (__appname__, __version__, __copyright__,
                        __developer__, __contact__, __website__)


PROGRAM = f'{__appname__}d'
USAGE = f"""\
usage: {PROGRAM} ...
       {PROGRAM} [--help] [--version]

{__doc__}
This program should not be called directly.\
"""
EPILOG = f"""\
Documentation and issue tracking at:
{__website__}

Copyright {__copyright__}
{__developer__} {__contact__}.\
"""
HELP = f"""\
{USAGE}

options:
-h, --help             Show this message and exit.
-v, --version          Show the version and exit.

{EPILOG}
"""

# initialize module level logger
log = get_logger(PROGRAM)


class RefittDaemon(Application):
    """Application class for the refitt service daemon, `refittd`."""

    interface = ArgumentParser(PROGRAM, USAGE, HELP)
    interface.add_argument('--version', version=__version__, action='version')

    def run(self) -> None:
        """Start the refitt service daemon."""
        log.info('starting service')


def main() -> int:
    """Entry-point for `refittd` console application."""
    return RefittDaemon.main()
