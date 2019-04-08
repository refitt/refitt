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
Command line argument parsing.

This module provides a modification to the standard `argparse.ArgumentParser`.
Instead of allowing it to construct usage and help statements, this
`ArgumentParser` takes a pre-constructed usage and print string and uses
those instead. Further, it suppresses the exit behavior and always raises a
`ParserError` instead of trying to exit the program immediately.
"""

# standard libs
import argparse as _argparse

# elevate to this module
Namespace = _argparse.Namespace


class ParserError(Exception):
    """Exceptions originating from `argparse`."""


class ArgumentParser(_argparse.ArgumentParser):
    """
    Variant of `argparse.ArgumentParser` that raises ParserError instead of
    calling `sys.exit` and expects hard-coded usage and help text.

    Example:
        >>> from refitt.core.parser import ArgumentParser
        >>> interface = ArgumentParser('my_app', ...)
        >>> interface.add_argument('--verbose', action_group='store_true')
    """

    def __init__(self, program: str, usage_text: str, help_text: str) -> None:
        """
        Explicitly provide `usage_text` and `help_text`.

        program: str
            Name of program (e.g., `os.path.basename(sys.argv[0])`).
        usage_text: str
            Full text of program "usage" statement.
        help_text: str
            Full text of program "help" statement.

        See Also:
        `argparse.ArgumentParser`
        """
        self.program = program
        self.usage_text = usage_text
        self.help_text = help_text
        super().__init__(prog=program, usage=usage_text, allow_abbrev=False)

    # prevents base class from trying to build up help text
    def format_help(self) -> str:
        return self.help_text

    # prevents base class from trying to build up usage text
    def format_usage(self) -> str:
        return self.usage_text

    # messages will be printed manually
    def print_usage(self, *args, **kwargs) -> None:
        return  # don't allow parser to print usage

    # don't allow base class attempt to exit
    def exit(self, status: int = 0, message: str = None) -> None:
        raise ParserError(message)

    # simple raise, no printing
    def error(self, message: str) -> None:
        raise ParserError(message)
