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

"""User/facility profile management."""

# standard libs
import json

# internal libs
from ..core.logging import logger
from .interface import execute

# external libs
from sqlalchemy.sql import text

# initialize module level logger
log = logger.with_name(f'refitt.database.user')


UPDATE_QUERY = """\
INSERT INTO "user"."user" (user_id, user_first_name, user_last_name, user_email, user_alias, user_profile)
VALUES (:user_id, :user_first_name, :user_last_name, :user_email, :user_alias, :user_profile)
ON CONFLICT (user_id) DO UPDATE
    SET user_first_name = excluded.user_first_name,
        user_last_name  = excluded.user_last_name,
        user_email      = excluded.user_email,
        user_alias      = excluded.user_alias,
        user_profile    = excluded.user_profile;
"""

INSERT_QUERY = """\
INSERT INTO "user"."user" (user_first_name, user_last_name, user_email, user_alias, user_profile)
VALUES (:user_first_name, :user_last_name, :user_email, :user_alias, :user_profile)
"""


def insert_user(profile: dict) -> None:
    """
    Insert/update user profile in database.

    Arguments
    ---------
    profile: dict
        User profile dictionary to be inserted.
        This will be JSON serialized.
    """
    if 'user_id' in profile:
        execute(text(UPDATE_QUERY), user_id=profile['user_id'], user_first_name=profile['user_first_name'],
                user_last_name=profile['user_last_name'], user_email=profile['user_email'],
                user_alias=profile['user_alias'], user_profile=json.dumps(profile))
    else:
        execute(text(INSERT_QUERY), user_first_name=profile['user_first_name'],
                user_last_name=profile['user_last_name'], user_email=profile['user_email'],
                user_alias=profile['user_alias'], user_profile=json.dumps(profile))
