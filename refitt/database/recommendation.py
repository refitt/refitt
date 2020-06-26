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

"""Manage recommendations."""

# type annotations
from typing import List

# internal libs
from ..core.logging import Logger
from .core.interface import execute, _select, Table

# external libs
from sqlalchemy import sql
from pandas import DataFrame


# initialize module level logger
log = Logger(__name__)

# interface
recommendation_group = Table('recommendation', 'recommendation_group')
recommendation = Table('recommendation', 'recommendation')


CREATE_GROUP = sql.text("""\
INSERT INTO "recommendation"."recommendation_group" (recommendation_group_id)
VALUES (DEFAULT)
RETURNING recommendation_group_id;
""")


def new_group() -> int:
    """
    Create a new recommendation group.

    Returns
    -------
    group_id: int
        The newly generated "recommendation_group_id".
    """
    group_id = execute(CREATE_GROUP).fetchone()[0]
    log.info(f'created group (recommendation_group_id={group_id})')
    return group_id


def get_group() -> int:
    """
    Query for the most recent "recommendation_group_id".

    Returns
    -------
    group_id: int
        The most recent "recommendation_group_id".
    """
    return int(recommendation_group.select(['recommendation_group_id'], orderby='recommendation_group_id',
                                           set_index=False, limit=1).iloc[0].recommendation_group_id)


def add(objects: List[int], group_id: int, user_id: int) -> None:
    """
    Add `object_id` to "recommendation" table.

    Parameters
    ----------
    objects: List[int]
        The object_id's to be inserted.

    group_id: int
        The "recommendation_group_id".

    user_id: int
        The "user_id".
    """
    records = DataFrame({'object_id': objects}).assign(recommendation_group_id=group_id,
                                                       user_id=user_id)
    recommendation.insert(records)
    log.info(f'recommended {len(records)} objects (user_id={user_id}, recommendation_group_id={group_id})')


QUERY = """\
SELECT
    rec.object_id,
    obj.object_name,
    typ.object_type_name as object_type,
    obj.object_aliases,
    obj.object_ra,
    obj.object_dec,
    obj.object_redshift,
    rec.recommendation_id,
    rec.recommendation_group_id

FROM
    recommendation.recommendation AS rec

LEFT JOIN
    observation.object AS obj
    ON rec.object_id = obj.object_id

LEFT JOIN
    observation.object_type AS typ
    ON obj.object_type_id = typ.object_type_id

WHERE
        rec.user_id = {user_id}
    AND rec.recommendation_group_id = {recommendation_group_id}
"""

QUERY_PREVIOUS = """\
    AND rec.recommendation_id > {previous}
"""


def get(user_id: int, group_id: int = None, limit: int = None,
        previous: int = None) -> DataFrame:
    """
    Query for objects recommended to the user.

    Parameters
    ----------
    user_id: int
        The "user_id" from "user"."user".

    group_id: int (default: None)
        The "recommendation_group_id" for the recommendations. If None, `get_group` is
        called to fetch the most recent group.

    limit: int (default: None)
        Limit the number of returned recommendations. Translates to the underlying SQL
        query.

    previous: int (default: None)
        The "recommendation_id" of the last object from a previous call. This allows for
        incremental retrieval of one or more recommendations. If specified, the returned
        value is a dictionary with {recommendation_id: object_id ...}.

    Returns
    -------
    objects: `pandas.DataFrame`
        The objects recommended to the user. The dataframe consists of information
        from a multipart join from both the "observation"."object" and
        "observation"."object_type" tables.

    See Also
    --------
    get_group:`refitt.database.recommendation.get_group`
    """
    gid = group_id if group_id is not None else get_group()
    query = QUERY.format(user_id=user_id, recommendation_group_id=gid)
    if previous is not None:
        query += QUERY_PREVIOUS.format(previous=previous)
    return _select(query).set_index('object_id')
