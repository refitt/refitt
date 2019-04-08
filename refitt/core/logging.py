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
Logging configuration.

REFITT uses the `logalpha` package for logging functionality. Console applications
and routines provided by the package use the `get_logger` method to acquire a `BaseLogger`
instance initialized as per the runtime configuration in use.

"""

# standard libraries
import os
from datetime import datetime

# external libraries
from logalpha import BaseLogger, ConsoleHandler, FileHandler

# internal library
from ..__meta__ import __appname__
from .config import get_config


def get_logger(name: str = None, console: bool = True) -> BaseLogger:
    """
    Constructs a logger.

    Arguments
    ---------
    name: str = None
        Message prefix to use.

    console: bool = True
        If False, suppress adding a ConsoleHandler.

    Returns
    -------
    BaseLogger: `logalpha.BaseLogger`
        An initialized logging manager.

    Example
    -------
        >>> from refitt.core.logging import get_logger
        >>> log = get_logger('example')
        >>> log.info('some message')
        info 12:34:56 example: some message

    See Also
    --------
    `refitt.core.config`:
        Parsing runtime configuration.
    """

    config    = get_config()
    TIMESTAMP = datetime.now().strftime('%Y%m%d')
    LOGFILE   = f'{config["logs"]}/{__appname__}-{TIMESTAMP}.log'
    LOGSITE   = os.path.dirname(LOGFILE)
    os.makedirs(LOGSITE, exist_ok=True)

    handlers = []  # List[BaseHandler]

    if name is None:
        handlers.append(FileHandler(level=config['loglevel'],
                                    template='{LEVEL} {time} [' + config['host'] + '] {message}',
                                    time=lambda: datetime.now().strftime('%Y%m%d-%H:%M:%S'),
                                    file=LOGFILE))
        if console is True:
            handlers.append(ConsoleHandler(level=config['loglevel'],
                                           template='{level} {time} {message}',
                                           time=lambda: datetime.now().strftime('%H:%M:%S')))
    else:
        if config['host'] is not None:
            template = '{LEVEL} {time} ' + f'[{config["host"]}] {name}: ' + '{message}'
        else:
            template = '{LEVEL} {time} ' + f'{name}: ' + '{message}'
        handlers.append(FileHandler(level=config['loglevel'],
                                    template=template, file=LOGFILE,
                                    time=lambda: datetime.now().strftime('%Y%m%d-%H:%M:%S')))
        if console is True:
            handlers.append(ConsoleHandler(level=config['loglevel'],
                                           template='{level} {time} ' + name + ': {message}',
                                           time=lambda: datetime.now().strftime('%H:%M:%S')))

    return BaseLogger(handlers)
