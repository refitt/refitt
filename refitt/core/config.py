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

"""Defines default configuration and reads from /etc/refitt.yml."""

# standard libs
import os
from subprocess import check_output
from typing import Dict


# environment variables
from ..__meta__ import __appname__


def get_config() -> Dict[str, str]:
    """Load and validate configuration file."""

    HOST = check_output('hostname').decode().strip()
    TEMP = os.getenv('CLUSTER_SCRATCH', '/tmp')
    HOME = f'{TEMP}/{__appname__}'
    DATA = f'{HOME}/data'
    LOGS = f'{HOME}/logs'
    RUN  = f'{HOME}/run'

    PREFIX = __appname__.upper()
    LOGLEVEL = os.getenv(f'{PREFIX}_LOGLEVEL', 'INFO')

    # enforce existence of directories
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(LOGS, exist_ok=True)

    return {'host': HOST,
            'temp': TEMP,
            'data': DATA,
            'logs': LOGS,
            'loglevel': LOGLEVEL,
            'run': RUN
            }
