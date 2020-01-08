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

"""Subscribe to remote data brokers and stream alerts."""

# type annotations
from __future__ import annotations

# standard libs
import os
import functools

# internal libs
from ....core.config import config
from ....core.exceptions import log_and_exit
from ....core.logging import Logger, SYSLOG_HANDLER
from ....stream.antares import AntaresClient
from ....__meta__ import __appname__, __copyright__, __developer__, __contact__, __website__

# external libs
from cmdkit.app import Application, exit_status
from cmdkit.cli import Interface


# program name is constructed from module file name
PROGRAM = f'{__appname__} service stream'
PADDING = ' ' * len(PROGRAM)

USAGE = f"""\
usage: {PROGRAM} <broker> <topic> [--output-directory DIR] [--filter NAME]
       {PADDING} [--key KEY] [--token TOKEN] [--debug | --verbose] [--syslog]
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

arguments:
<broker>                       Name of broker (e.g., "antares").
<topic>                        Name of topic (e.g., "extragalactic").

options:
--key                   STR    API key for broker.
--token                 STR    API token for broker.
-o, --output-directory  DIR    Path to directory for alert files (default $CWD).
-f, --filter            NAME   Name of filter to reject alerts.
-d, --debug                    Show debugging messages.
-v, --verbose                  Show information messages.
    --syslog                   Use syslog style messages.
-h, --help                     Show this message and exit.

{EPILOG}
"""

# initialize module level logger
log = Logger.with_name('.'.join(PROGRAM.split()))

# available streams
client = {
    'antares': AntaresClient,
}


class Stream(Application):
    """Subscribe to remote data brokers and stream alerts."""

    interface = Interface(PROGRAM, USAGE, HELP)

    # input file containing list of candidates/alerts
    broker: str = None
    interface.add_argument('broker')

    topic: str = None
    interface.add_argument('topic')

    key: str = None
    interface.add_argument('--key', default=key)

    token: str = None
    interface.add_argument('--token', default=token)

    filter_name: str = 'none'
    interface.add_argument('--filter', dest='filter_name', default=filter_name)

    output_directory: str = os.getcwd()
    interface.add_argument('-o', '--output-directory', default=output_directory)

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
        """Run Refitt pipeline."""

        if self.broker not in client:
            log.critical(f'"{self.broker}" is not an available broker.')
            return

        if self.key is None:
            try:
                self.key = config['stream'][self.broker]['key']
                log.debug(f'loaded api key from configuration file')
            except KeyError:
                log.critical(f'No `--key` given and "stream.{self.broker}.key" not found in config.')
                return

        if self.token is None:
            try:
                self.token = config['stream'][self.broker]['token']
                log.debug(f'loaded api token from configuration file')
            except KeyError:
                log.critical(f'No `--token` given and "stream.{self.broker}.token" not found in config.')
                return

        Client = client[self.broker]
        filter_name = f'filter_{self.filter_name}'
        if not hasattr(Client, filter_name):
            log.critical(f'Local filter "{self.filter_name}" does not exist for {self.broker}.')
            return

        local_filter = getattr(Client, filter_name)

        log.info(f'connecting to {self.broker}')
        with Client(self.topic, (self.key, self.token)) as stream:
            log.info(f'initiating stream (broker={self.broker} topic={self.topic} filter={self.filter_name})')

            for alert in stream:
                log.info(f'received {self.broker}:{alert.alert_id}')
                if local_filter(alert) is False:
                    log.info(f'{self.broker}:{alert.alert_id} rejected by {filter_name}')
                else:
                    log.info(f'{self.broker}:{alert.alert_id} accepted by {filter_name}')
                    filepath = os.path.join(self.output_directory, f'{alert.alert_id}.json')
                    alert.to_file(filepath)
                    log.info(f'{self.broker}:{alert.alert_id} written to {filepath}')

    def __enter__(self) -> Stream:
        """Initialize resources."""

        if self.syslog:
            log.handlers[0] = SYSLOG_HANDLER
        if self.debug:
            log.handlers[0].level = log.levels[0]
        elif self.verbose:
            log.handlers[0].level = log.levels[1]
        else:
            log.handlers[0].level = log.levels[2]

        return self

    def __exit__(self, *exc) -> None:
        """Release resources."""