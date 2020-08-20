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

"""Send an email."""

# type annotations
from __future__ import annotations
from typing import List

# standard libs
import sys
import functools

# internal libs
from ....comm.notice.email import UserAuth, Mail, Server, templates, TEMPLATES
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, cli_setup
from ....core.config import config, ConfigurationError, expand_parameters
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface, ArgumentError


# program name is constructed from module file name
PROGRAM = f'{__appname__} notify email'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} ADDR [ADDR ...] [--from PROFILE] [--subject MSG]
       {PADDING} [--cc ADDR [ADDR ...]] [--bcc ADDR [ADDR ...]]
       {PADDING} [--message FILE] [--plain | --html] [--attach FILE [FILE ...]]
       {PADDING} [--template NAME [--opts ARG [ARG ...]]]
       {PADDING} [--dry-run] [--debug | --verbose] [--syslog]
       {PADDING} [--help] [--list-templates]

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

If no template is provided, send an email with a custom message.
Use --plain/--html to specify the format of the message.

arguments:
ADDR                         Address of recipients.

options:
-f, --from      PROFILE      Name of mail profile.
-s, --subject   MSG          Subject of mail.
    --cc        ADDR...      Address of recipients (CC).
    --bcc       ADDR...      Address of recipients (BCC).
-m, --message   FILE         Path to mail body (default: stdin).
    --plain                  Send mail as plain text.
    --html                   Send mail as html.
-a, --attach    FILE         Paths to files to attach.
-t, --template  NAME         Name of mail template.
    --opts      ARG...       Arguments for template.
-d, --debug                  Show debugging messages.
-v, --verbose                Show information messages.
    --syslog                 Use syslog style messages.
    --dry-run                Show the raw MIME text.
-h, --help                   Show this message and exit.

extras:
    --list-templates         Show templates.

{EPILOG}
"""


# initialize module level logger
log = Logger(__name__)


def connection_refused(exc: ConnectionRefusedError) -> int:  # noqa: unused
    """The mail server refused the connection."""
    log.critical('mail server refused connection')
    return exit_status.runtime_error


class Email(Application):
    """Send an email."""

    interface = Interface(PROGRAM, USAGE, HELP)

    recipients: List[str] = []
    interface.add_argument('recipients', nargs='+', default=recipients)

    cc: List[str] = None
    interface.add_argument('--cc', nargs='+', default=cc)

    bcc: List[str] = None
    interface.add_argument('--bcc', nargs='+', default=bcc)

    profile: str = 'default'
    interface.add_argument('-f', '--from', default=profile, dest='profile')

    subject: str = None
    interface.add_argument('-s', '--subject', default=subject)

    message_file: str = None  # "-" for stdin
    interface.add_argument('-m', '--message', default=message_file, dest='message_file')

    message_type: str = 'plain'
    message_text: bool = True
    message_html: bool = False
    message_interface = interface.add_mutually_exclusive_group()
    message_interface.add_argument('--plain', action='store_true', dest='message_text')
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
    server: Server = None

    exceptions = {
        RuntimeError: functools.partial(log_and_exit, logger=log.critical,
                                        status=exit_status.runtime_error),
        ConfigurationError: functools.partial(log_and_exit, logger=log.critical,
                                              status=exit_status.bad_config),
        ConnectionRefusedError: connection_refused,
    }

    def run(self) -> None:
        """Send email."""
        if self.template is not None:
            self.run_template()
        else:
            self.run_basic()

    def run_template(self) -> None:
        """Send a template based email."""

        if self.message_file is not None:
            raise ArgumentError('cannot specify message file for template')

        if self.template not in templates:
            raise ArgumentError(f'template "{self.template}" not found')

        log.debug(f'using {self.template} template')
        Template = templates[self.template]
        if len(self.options) != Template.required:
            raise ArgumentError(f'"{self.template}" requires {Template.required} positional arguments '
                                f'but {len(self.options)} provided from --opts')

        self.mail = Template(*self.options, self.address, self.recipients,
                             subject=self.subject, cc=self.cc, bcc=self.bcc,
                             attach=self.attachments)
        if self.dry_run:
            print(self.mail)
        else:
            self.server.send(self.mail)
            self.log_message()

    def run_basic(self) -> None:
        """Send a basic email without any template."""

        if self.options:
            raise ArgumentError('cannot specify --opts w/out template')

        if self.message_file in (None, '-'):
            message = sys.stdin.read()
        else:
            with open(self.message_file, mode='r') as source:
                message = source.read()

        msg_type = 'text' if self.message_text else 'html'
        msg_form = {msg_type: message}
        self.mail = Mail(self.address, self.recipients,
                         subject=self.subject, cc=self.cc, bcc=self.bcc,
                         **{**msg_form, 'attach': self.attachments})

        if self.dry_run:
            print(self.mail)
        else:
            self.server.send(self.mail)
            self.log_message()

    def log_message(self) -> None:
        """Compose a logging message."""
        recipients = ', '.join(self.recipients)
        msg = f'sent email to {recipients}'
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

    def __enter__(self) -> Email:
        """Initialize resources."""

        cli_setup(self)

        # email configuration
        profile = config['mail']
        if self.profile not in profile:
            raise ConfigurationError(f'[mail.{self.profile}] not found')
        profile = config['mail'][self.profile]
        log.debug(f'using {self.profile} profile')

        self.address = profile.get('address', None)
        if self.address is None:
            raise ConfigurationError(f'[mail.{self.profile}] missing address')
        log.debug(f'sending from {self.address}')

        username = profile.get('username', None)
        if not any(field.startswith('password') for field in profile):
            password = None
        else:
            password = expand_parameters('password', profile)

        auth = None
        if username is None and password is None:
            log.debug('no username/password provided')
        elif username is None or password is None:
            raise ConfigurationError(f'must provide both username and password together')
        else:
            auth = UserAuth(username, password)

        host = profile.pop('host', '127.0.0.1')
        port = profile.pop('port', 0)
        log.debug(f'mail server is {host}:{port}')
        self.server = Server(host, port, auth)
        self.server.connect()
        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""
        # close message file if necessary
        if self.server is not None:
            self.server.disconnect()
