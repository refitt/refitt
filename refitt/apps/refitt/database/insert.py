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

"""Insert data into the REFITT database."""

# type annotations
from __future__ import annotations
from typing import List, Optional

# standard libs
import os
import sys
import functools

# internal libs
from .... import database
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError
import pandas


# program name is constructed from module file name
PROGRAM = f'{__appname__} database insert'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <schema>.<table> [--profile NAME] [--update]
       {PADDING} [--input PATH] [--format=FORMAT | ...]
       {PADDING} [--debug | --verbose] [--syslog]
       {PADDING} [--help]

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

Input is read from a file (or <stdout>). The format is implied by the file
extension (if present). If --update is specified, the primary key column must
be present. This will alter the existing data instead of appending.

arguments:
<schema>.<table>             Name of the table to insert.

options:
    --profile    NAME        Name of database profile (e.g., "test"). 
-i, --input      PATH        File path for input data.
-u, --update                 Alter existing data.
-f, --format     FORMAT      Name of input format. (default: CSV)
  , --ascii
  , --json
  , --csv
  , --feather
  , --excel
  , --html
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
-h, --help                   Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger(__name__)


class Insert(Application):
    """Insert data into the REFITT database."""

    interface = Interface(PROGRAM, USAGE, HELP)

    table: str = None
    interface.add_argument('table', metavar='<schema>.<table>')

    profile: Optional[str] = None
    interface.add_argument('--profile', default=profile)

    infile: str = None
    interface.add_argument('-i', '--infile', default=None)
    ext_map: dict = {'.csv': 'csv', '.xlsx': 'excel', '.feather': 'feather',
                     '.html': 'html', '.json': 'json'}

    input_format: str = None
    formats: List[str] = ['ascii', 'csv', 'json', 'excel', 'html', 'feather']
    format_group = interface.add_mutually_exclusive_group()
    format_group.add_argument('-f', '--format', choices=formats, dest='output_format')
    for option in formats:
        format_group.add_argument(f'--{option}', dest=f'format_{option}', action='store_true')

    delim: str = ','
    interface.add_argument('--delim', default=delim)

    update: bool = False
    interface.add_argument('-u', '--update', action='store_true')

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
    }

    def run(self) -> None:
        """Run insert."""

        if self.update:
            raise ArgumentError('--update is not implemented')

        schema, table = self.table.split('.')

        # extract map of any specified format flags
        format_flags = {option: getattr(self, f'format_{option}') for option in self.formats}

        # allow for format flags
        for input_format, selected in format_flags.items():
            if selected is True:
                self.input_format = input_format

        # if a file extension is present, determine sensible format
        if self.infile not in (None, '-') and self.input_format is None:
            _, file_ext = os.path.splitext(self.infile)
            if file_ext in self.ext_map:
                log.debug(f'known file extension: "{file_ext}"')
                self.input_format = self.ext_map[file_ext]
            elif self.input_format is None and not any(format_flags.values()):
                log.critical(f'filetype not implemented: "{file_ext}"')
                return

        if self.input_format is None:
            self.input_format = 'csv'

        # output is either a path or <stdout> instance
        if self.infile in (None, '-'):
            reader = lambda path: sys.stdin.read()
        elif self.input_format == 'ascii':
            reader = functools.partial(pandas.read_fwf)
        elif self.input_format == 'csv':
            reader = functools.partial(pandas.read_csv, sep=self.delim)
        elif self.input_format == 'json':
            reader = functools.partial(pandas.read_json, orient='records', lines=True)
        elif self.input_format == 'feather':
            reader = pandas.read_feather
        else:
            reader = getattr(pandas, f'read_{self.input_format}')

        infile_label = '<stdin>' if self.infile in (None, '-') else self.infile
        log.info(f'reading data from {infile_label} (format={self.input_format})')
        data = reader(self.infile)

        log.info(f'inserting {len(data)} records into "{schema}"."{table}"')
        database.insert(data, schema, table)

    def __enter__(self) -> Insert:
        """Initialize resources."""
        cli_setup(self)
        database.connect(profile=self.profile)
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        database.disconnect()
