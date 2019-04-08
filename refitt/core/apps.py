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

"""Console application infrastructure."""


# standard libs
from abc import ABC as AbstractBase, abstractmethod
from typing import List

# internal libs
from ..__meta__ import __appname__
from .parser import ArgumentParser, Namespace, ParserError
from .logging import BaseLogger, get_logger


EXIT_STATUS = {"SUCCESS":            0,
               "INFORMATION":        1,
               "BAD_ARGUMENT":       2,
               "BAD_CONFIGURATION":  3,
               "INTERRUPT":          4,
               "FAILURE":            5,
               "UNCAUGHT":           6}


class Application(AbstractBase):
    """
    Abstract base class for all application interfaces.
    """

    log: BaseLogger = get_logger(__appname__)
    interface: ArgumentParser = None
    ParserError: Exception = ParserError

    def __init__(self, **parameters) -> None:
        """Direct initialization sets `parameters`."""
        for name, value in parameters.items():
            setattr(self, name, value)

    @classmethod
    def from_cmdline(cls, cmdline: List[str] = None) -> 'Application':
        """Initialize via command line arguments (e.g., `sys.argv`)."""
        return cls.from_namespace(cls.interface.parse_args(cmdline))

    @classmethod
    def from_namespace(cls, namespace: Namespace) -> 'Application':
        """Initialize via existing namespace/namedtuple."""
        return cls(**vars(namespace))

    @classmethod
    def main(cls, cmdline: List[str] = None) -> int:
        """Entry-point for application."""
        try:
            if not cmdline:
                if hasattr(cls, 'ALLOW_NOARGS') and cls.ALLOW_NOARGS is True:
                    pass
                else:
                    print(cls.interface.usage_text, flush=True)
                    return EXIT_STATUS['INFORMATION']

            app = cls.from_cmdline(cmdline)
            app.run()

            return EXIT_STATUS['SUCCESS']

        except ParserError as error:
            message, = error.args
            if message:
                cls.log.critical(message)
            return EXIT_STATUS['BAD_ARGUMENT']

        except KeyboardInterrupt:
            cls.log.critical('keyboard-interrupt: going down now!')
            return EXIT_STATUS['INTERRUPT']

        except Exception as error:
            cls.log.critical(f'uncaught exception occurred!')
            raise error

    @abstractmethod
    def run(self) -> None:
        """Business-logic of the application."""
        raise NotImplementedError()
