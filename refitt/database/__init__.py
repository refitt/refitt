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


from . import client, config, interface, user, auth
from .interface import execute, select, insert

from .interface import user as user_schema, observation as observation_schema, \
    recommendation as recommendation_schema, model as model_schema, \
    message as message_schema

schema = {'user': user_schema, 'observation': observation_schema,
          'recommendation': recommendation_schema, 'model': model_schema,
          'message': message_schema}
