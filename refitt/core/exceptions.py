# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Common exceptions and error handling."""


# type annotations
from typing import Callable, Union, List

# standard libs
import os
import datetime
import traceback
import logging

# external libs
from cmdkit.app import exit_status

# internal libs
from .config import config, get_site
from ..comm.mail import Mail, UserAuth

# public interface
__all__ = ['log_exception', 'handle_exception', ]


# initialize module level logger
log = logging.getLogger(__name__)

def log_exception(exc: Exception, logger: Callable[[str], None], status: int) -> int:
    """Log the exception and exit with `status`."""
    logger(str(exc))
    return status


def handle_exception(logger: logging.Logger, exc: Exception) -> int:
    """Write exception to file and return exit code."""
    time = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    path = os.path.join(get_site()['log'], f'exception-{time}.log')
    with open(path, mode='w') as stream:
        print(traceback.format_exc(), file=stream)
    msg = str(exc).replace('\n', ' - ')
    logger.critical(f'{exc.__class__.__name__}: {msg}')
    logger.critical(f'Exception traceback written to {path}')
    if 'exceptions' in config and 'mailto' in config.exceptions:
        email_exception(config.exceptions.mailto, path)
        logger.critical(f'Exception traceback mailed to {config.exceptions.mailto}')
    return exit_status.uncaught_exception


MAIL = """\
This is an automated message from the REFITT system. \
An uncaught exception has occurred. \
Please see attached.

"""


def email_exception(recipient: Union[str, List[str]], filepath: str) -> None:
    """Send an email to configured recipient."""
    if 'mail' not in config:
        log.error('Missing \'mail\' section in configuration')
        return
    try:
        address = config.mail.address
        log.debug(f'Sending from {address}')
    except AttributeError:
        log.error('Missing \'mail.address\'')
        return
    try:
        username = config.mail.username
    except AttributeError:
        username = None
    try:
        password = config.mail.password
    except AttributeError:
        password = None
    auth = None
    if username is None and password is None:
        log.debug('No username/password provided')
    elif username is None or password is None:
        log.error(f'Must provide username and password together')
        return
    else:
        auth = UserAuth(username, password)
    host = config.mail.get('host', '127.0.0.1')
    port = config.mail.get('port', 0)
    mail = Mail(address, recipient, text=MAIL, attach=filepath,
                subject='Uncaught exception occurred within REFITT')
    mail.send(host, port, auth)
