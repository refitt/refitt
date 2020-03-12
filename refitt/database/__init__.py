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

"""Toplevel API for REFITT's database."""


from . import config, interface, user, auth
from .client import DatabaseClient, connect, disconnect
from .interface import execute, select, insert

# group schema instances together
data = {'user': interface.user,
        'observation': interface.observation,
        'recommendation': interface.recommendation,
        'model': interface.model,
        'message': interface.message}
