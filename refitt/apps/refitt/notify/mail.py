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

"""Send mail."""

# type annotations
from __future__ import annotations
from typing import Tuple, List, Optional

# standard libs
import sys
import logging
import functools
from smtplib import SMTPAuthenticationError

# internal libs
from ....comm.mail import UserAuth, Mail, MailServer, templates, TEMPLATES
from ....core.exceptions import log_exception
from ....core.config import config, ConfigurationError

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


PROGRAM = f'refitt notify mail'
PADDING = ' ' * len(PROGRAM)
USAGE = f"""\
usage: {PROGRAM} [-h] ADDR [ADDR ...] [-m MESSAGE | -m @FILE [--text | --html]] [-s SUBJECT]
       {PADDING} [--cc ADDR [ADDR ...]] [--bcc ADDR [ADDR ...]] [--attach FILE [FILE ...]]
       {PADDING} [--template NAME [--opts ARG [ARG ...]]]
       {PADDING} [--dry-run] [--list-templates]
{__doc__}\
"""

HELP = f"""\
{USAGE}

If no template is provided, send an email with a custom message.
Use --text/--html to specify the format of the message.

arguments:
ADDR                         Address of recipients.

options:
-s, --subject   TEXT         Subject of mail.
    --cc        ADDR...      Address(es) of recipients (CC).
    --bcc       ADDR...      Address(es) of recipients (BCC).
-m, --message   SOURCE       The message or path (e.g., @file.txt, @- for <stdin>).
    --text                   Send mail as plain text (default).
    --html                   Send mail as html.
-a, --attach    FILE...      Path(s) to file(s) to attach.
-t, --template  NAME         Name of template.
    --opts      ARG...       Positional arguments for template.
    --dry-run                Show the raw MIME text and exit.
-h, --help                   Show this message and exit.

extras:
    --list-templates         Show available templates and exit.\
"""


# application logger
log = logging.getLogger('refitt')


def connection_refused(exc: ConnectionRefusedError) -> int:
    """The mail server refused the connection."""
    log.critical(f'Mail server refused connection: {exc}')
    return exit_status.runtime_error


def connection_timeout(exc: TimeoutError) -> int:
    """Failed to connect because the operation timed out.."""
    log.critical(f'Connection failed: {exc}')
    return exit_status.runtime_error


def authentication_failed(exc: SMTPAuthenticationError) -> int:
    """The mail server refused the connection."""
    code, message = exc.args
    log.critical(f'Authentication failed [{code}]: {message.decode()}')
    return exit_status.runtime_error


class MailApp(Application):
    """Application class for mail notification entry-point."""

    interface = Interface(PROGRAM, USAGE, HELP)

    recipients: List[str] = []
    interface.add_argument('recipients', nargs='+', default=recipients)

    cc: List[str] = None
    interface.add_argument('--cc', nargs='+', default=cc)

    bcc: List[str] = None
    interface.add_argument('--bcc', nargs='+', default=bcc)

    subject: str = None
    interface.add_argument('-s', '--subject', default=subject)

    message_source: str = None  # 'None' is required by templates
    interface.add_argument('-m', '--message', default=message_source, dest='message_source')

    message_text: bool = True
    message_html: bool = False
    message_interface = interface.add_mutually_exclusive_group()
    message_interface.add_argument('--text', action='store_true', dest='message_text')
    message_interface.add_argument('--html', action='store_true', dest='message_html')

    attachments: List[str] = []
    interface.add_argument('-a', '--attach', nargs='+', default=attachments, dest='attachments')

    template: str = None
    interface.add_argument('-t', '--template', default=None)

    options: List[str] = []
    interface.add_argument('--opts', nargs='+', default=options, dest='options')

    debug: bool = False
    verbose: bool = False
    logging_interface = interface.add_mutually_exclusive_group()
    logging_interface.add_argument('-d', '--debug', action='store_true')
    logging_interface.add_argument('-v', '--verbose', action='store_true')

    syslog: bool = False
    interface.add_argument('--syslog', action='store_true')

    dry_run: bool = False
    interface.add_argument('--dry-run', action='store_true')

    list_templates: bool = False
    interface.add_argument('--list-templates', version=TEMPLATES, action='version')

    mail: Mail = None
    address: str = None
    server: MailServer = None

    exceptions = {
        RuntimeError: functools.partial(log_exception, logger=log.critical,
                                        status=exit_status.runtime_error),
        ConfigurationError: functools.partial(log_exception, logger=log.critical,
                                              status=exit_status.bad_config),
        SMTPAuthenticationError: authentication_failed,
        TimeoutError: connection_timeout,
        ConnectionRefusedError: connection_refused,
    }

    def run(self) -> None:
        """Send email."""
        if self.template is not None:
            self.prepare_template()
        else:
            self.prepare_generic()
        if self.dry_run:
            print(self.mail)
        else:
            self.server.send(self.mail)
            self.log_message()

    @functools.cached_property
    def message(self) -> Optional[str]:
        """Body of message."""
        if self.message_source is None:
            return None
        elif self.message_source[0] != '@':
            return self.message_source
        else:
            return self.load_file(self.message_source[1:])

    @staticmethod
    def load_file(path: str) -> str:
        """Load contents of file from `path`."""
        if path == '-':
            return sys.stdin.read()
        else:
            try:
                with open(path, mode='r') as stream:
                    return stream.read()
            except FileNotFoundError as error:
                raise RuntimeError(f'File not found \'{path}\'') from error

    def prepare_template(self) -> None:
        """Prepare a template based email."""
        if self.message_source is not None:
            raise ArgumentError('Cannot specify message file for template')
        if self.template not in templates:
            raise ArgumentError(f'Template \'{self.template}\' not found')
        log.debug(f'Using template \'{self.template}\'')
        template = templates[self.template]
        if len(self.options) != template.required:
            raise ArgumentError(f'Template \'{self.template}\' requires {template.required} '
                                f'positional arguments but {len(self.options)} provided from --opts')
        self.mail = template(*self.options, self.address, self.recipients,
                             subject=self.subject, cc=self.cc, bcc=self.bcc,
                             attach=self.attachments)

    def prepare_generic(self) -> None:
        """Send a basic email without any template."""
        if self.options:
            raise ArgumentError('Cannot specify --opts w/out template')
        msg_type = 'text' if not self.message_html else 'html'
        msg_form = {msg_type: self.message}
        self.mail = Mail(self.address, self.recipients,
                         subject=self.subject, cc=self.cc, bcc=self.bcc,
                         **{**msg_form, 'attach': self.attachments})

    def log_message(self) -> None:
        """Compose a logging message."""
        recipients = ', '.join(self.recipients)
        msg = f'Sent mail to {recipients}'
        if self.attachments:
            count = len(self.attachments)
            msg += f' [{count} files]'
        if self.cc:
            count = len(self.cc)
            msg += f' [{count} CC]'
        if self.bcc:
            count = len(self.bcc)
            msg += f' [{count} BCC]'
        log.info(msg)

    def __enter__(self) -> MailApp:
        """Initialize resources."""
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        self.disconnect()

    def connect(self) -> None:
        """Connect to remote mail server."""
        host, port, auth = self.get_config()
        self.server = MailServer(host, port, auth)
        self.server.connect()

    def disconnect(self) -> None:
        """Disconnect from remote mail server."""
        if self.server is not None:
            self.server.disconnect()

    def get_config(self) -> Tuple[str, int, Optional[UserAuth]]:
        """Construct user authentication and host/port values."""
        self.check_config()
        self.get_address()
        auth = self.get_auth(*self.get_credentials())
        host = config.mail.get('host', '127.0.0.1')
        port = config.mail.get('port', 0)
        log.debug(f'Mail server is {host}:{port}')
        return host, port, auth

    @staticmethod
    def check_config() -> None:
        """Check that we have a configuration."""
        if 'mail' not in config:
            raise ConfigurationError('Missing \'mail\' section in configuration')

    def get_address(self) -> None:
        """Get the address from the configuration."""
        try:
            self.address = config.mail.address
            log.debug(f'Sending from {self.address}')
        except AttributeError as error:
            raise ConfigurationError('Missing \'mail.address\'') from error

    @staticmethod
    def get_credentials() -> Tuple[Optional[str], Optional[str]]:
        """Get username and password from configuration."""
        try:
            username = config.mail.username
        except AttributeError:
            username = None
        try:
            password = config.mail.password
        except AttributeError:
            password = None
        return username, password

    @staticmethod
    def get_auth(username: Optional[str], password: Optional[str]) -> Optional[UserAuth]:
        """Create `UserAuth` from optional username and password."""
        auth = None
        if username is None and password is None:
            log.debug('No username/password provided')
        elif username is None or password is None:
            raise ConfigurationError(f'Must provide username and password together')
        else:
            auth = UserAuth(username, password)
        return auth
