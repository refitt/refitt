# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Common exceptions and error handling."""


# type annotations
from typing import Callable

# standard libs
import os
import datetime
import traceback
from logging import Logger

# external libs
from cmdkit.app import exit_status

# internal libs
from .config import get_site

# public interface
__all__ = ['log_exception', 'handle_exception', ]


def log_exception(exc: Exception, logger: Callable[[str], None], status: int) -> int:
    """Log the exception and exit with `status`."""
    logger(str(exc))
    return status


def handle_exception(logger: Logger, exc: Exception) -> int:
    """Write exception to file and return exit code."""
    time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    path = os.path.join(get_site()['log'], f'exception-{time}.log')
    with open(path, mode='w') as stream:
        print(traceback.format_exc(), file=stream)
    msg = str(exc).replace('\n', ' - ')
    logger.critical(f'{exc.__class__.__name__}: {msg}')
    logger.critical(f'Exception traceback written to {path}')
    return exit_status.uncaught_exception
