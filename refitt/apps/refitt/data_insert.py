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

"""Insert data into REFITT's database."""

# standard libs
import os
import sys
import functools

# internal libs
from ... import database
from ...core.logging import logger
from ...__meta__ import (__appname__, __copyright__, __developer__,
                         __contact__, __website__)

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface

# type annotations
from typing import List

# external libs
import pandas


# program name is constructed from module file name
NAME = os.path.basename(__file__)[:-3].replace('_', '.')
PROGRAM = f'{__appname__} {NAME}'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <schema>.<table> [--input PATH] [--format=FORMAT | ...] [--update] [--debug]
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
-i, --input      PATH        File path for input data.
-u, --update                 Alter existing data.
-d, --debug                  Show debugging messages.
-h, --help                   Show this message and exit.

formats:
-f, --format     FORMAT      Name of input format. (default: CSV)
  , --ascii
  , --json
  , --csv
  , --feather
  , --excel
  , --html

{EPILOG}
"""

# initialize module level logger
log = logger.with_name(f'{__appname__}.{NAME}')


class DataInsertApp(Application):

    interface = Interface(PROGRAM, USAGE, HELP)

    table: str = None
    interface.add_argument('table', metavar='<schema>.<table>')

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
    interface.add_argument('-d', '--debug', action='store_true')

    def run(self) -> None:
        """Run insert."""

        if self.debug:
            for handler in log.handlers:
                handler.level = log.levels[0]

        if self.update:
            log.warning('The --update feature is not currently implemented')

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
            self.infile = sys.stdin

        # determine reader method
        if self.input_format == 'ascii':
            reader = functools.partial(pandas.read_fwf)
        elif self.input_format == 'csv':
            reader = functools.partial(pandas.read_csv, sep=self.delim)
        elif self.input_format == 'json':
            reader = functools.partial(pandas.read_json, orient='records', lines=True)
        elif self.input_format == 'feather':
            reader = pandas.read_feather
        else:
            reader = getattr(pandas, f'read_{self.input_format}')

        log.debug(f'reading data from {self.infile} (format={self.input_format})')
        data = reader(self.infile)

        log.debug(f'inserting {len(data)} records into "{schema}"."{table}"')
        database.schema[schema][table].insert(data)


# inherit docstring from module
DataInsertApp.__doc__ = __doc__
