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
from __future__ import annotations
from typing import List, Dict, Any, Optional, Union

# standard libs
import json
from datetime import datetime

# internal libs
from ..core.config import config, ConfigurationError
from ..core.logging import Logger
from .core.interface import execute, Interface, Table, Record, RecordNotFound, _select
from .core import client

# external libs
from sqlalchemy import sql
from pandas import DataFrame
from pandas._libs.tslibs.timestamps import Timestamp


# initialize module level logger
log = Logger(__name__)

# interface
recommendation_group = Table('recommendation', 'recommendation_group')
recommendation = Table('recommendation', 'recommendation')


class RecommendationGroupNotFound(RecordNotFound):
    """The recommendation_group record was not found."""


_UPDATE_RECOMMENDATION_GROUP = """\
INSERT INTO "recommendation"."recommendation_group" (recommendation_group_id, recommendation_group_time)
VALUES (:recommendation_group_id, :recommendation_group_time)
ON CONFLICT (recommendation_group_id) DO UPDATE
    SET recommendation_group_time = excluded.recommendation_group_time;
"""


_INSERT_RECOMMENDATION_GROUP = """\
INSERT INTO "recommendation"."recommendation_group" (recommendation_group_time)
VALUES (:recommendation_group_time)
RETURNING recommendation_group_id;
"""


_NEW_RECOMMENDATION_GROUP = """\
INSERT INTO "recommendation"."recommendation_group" (recommendation_group_time)
VALUES (DEFAULT)
RETURNING recommendation_group_id;
"""


_NEAREST_RECOMMENDATION_GROUP = """\
SELECT recommendation_group_id, recommendation_group_time
FROM "recommendation"."recommendation_group"
WHERE recommendation_group_time = (
    SELECT max(recommendation_group_time) FROM "recommendation"."recommendation_group"
    WHERE recommendation_group_time <= :timestamp
)
ORDER BY recommendation_group_time DESC
LIMIT 1;
"""


_REMOVE_RECOMMENDATION_GROUP = """\
DELETE FROM "recommendation"."recommendation_group"
WHERE recommendation_group_id = :recommendation_group_id;
"""


_SELECT_GROUP = """\
SELECT
    recommendation_group.recommendation_group_id,
    recommendation_group.recommendation_group_time

FROM
    recommendation.recommendation_group as recommendation_group

WHERE
"""


# NOTE: one of the before clauses will always be used
_SELECT_GROUP_BEFORE_ID = """\
    recommendation_group.recommendation_group_id <= :before_id
"""


_SELECT_GROUP_BEFORE_TIME = """\
    recommendation_group.recommendation_group_time <= :before_time
"""


_SELECT_GROUP_AFTER_ID = """\
    AND  recommendation_group.recommendation_group_id > :after_id
"""


_SELECT_GROUP_AFTER_TIME = """\
    AND  recommendation_group.recommendation_group_time > :after_time
"""


_SELECT_GROUP_BY_TIME = """\
ORDER BY recommendation_group.recommendation_group_time DESC
"""


_SELECT_GROUP_LIMIT = """\
LIMIT :limit
"""



class RecommendationGroup(Record):
    """
    A record from the "recommendation"."recommendation_group" table.

    Example
    -------
    >>> from refitt.database.recommendation import RecommendationGroup
    >>> RecommendationGroup.new()
    RecommendationGroup(recommendation_group_id=2,
                        recommendation_group_time=datetime.datetime(2020, 7, 1, 13, 21, 21, 951047, tzinfo=<UTC>))
    """

    _fields = ('recommendation_group_id', 'recommendation_group_time')
    _masked = False

    _recommendation_group_id: Optional[int] = None
    _recommendation_group_time: Optional[datetime] = None

    _FACTORIES = {'recommendation_group_id': 'from_id', }

    def __init__(self, *instance, **fields) -> None:
        """Optionally blank initialization."""
        if instance or fields:
            super().__init__(*instance, **fields)

    @property
    def recommendation_group_id(self) -> Optional[int]:
        return self._recommendation_group_id

    @recommendation_group_id.setter
    def recommendation_group_id(self, value: int) -> None:
        _recommendation_group_id = None if value is None else int(value)
        if _recommendation_group_id is not None and _recommendation_group_id < 0:
            raise ValueError(f'{self.__class__.__name__}.recommendation_group_id expects positive integer')
        else:
            self._recommendation_group_id = _recommendation_group_id

    @property
    def recommendation_group_time(self) -> Optional[datetime]:
        return self._recommendation_group_time

    @recommendation_group_time.setter
    def recommendation_group_time(self, value: datetime) -> None:
        if value is None:
            self._recommendation_group_time = None
        elif isinstance(value, Timestamp):
            self._recommendation_group_time = value.to_pydatetime()
        elif isinstance(value, datetime):
            self._recommendation_group_time = value
        else:
            raise TypeError(f'{self.__class__.__name__}.recommendation_group_time expects {type(datetime)}')

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> RecommendationGroup:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise RecommendationGroupNotFound(*error.args) from error

    @classmethod
    def from_id(cls, recommendation_group_id: int, interface: Interface = None) -> RecommendationGroup:
        """Get recommendation_group record from `recommendation_group_id`."""
        return cls._from_unique(recommendation_group, 'recommendation_group_id', recommendation_group_id, interface)

    def to_database(self) -> int:
        """
        Add recommendation_group record to the database.
        If the recommendation_group_id is defined, the recommendation_group_time must also be defined.
        An undefined recommendation_group_id will be inserted as a new record and the new id returned.
        """
        data = self.to_dict()
        recommendation_group_id = data.pop('recommendation_group_id')
        if recommendation_group_id:
            execute(_UPDATE_RECOMMENDATION_GROUP, recommendation_group_id=recommendation_group_id, **data)
            log.info(f'updated recommendation_group: recommendation_group_id={recommendation_group_id}')
        else:
            if data['recommendation_group_time'] is None:
                ((recommendation_group_id, ),) = execute(_NEW_RECOMMENDATION_GROUP)
            else:
                ((recommendation_group_id, ),) = execute(_INSERT_RECOMMENDATION_GROUP, **data)
            log.info(f'added recommendation_group: recommendation_group_id={recommendation_group_id}')
        return recommendation_group_id

    @classmethod
    def new(cls) -> RecommendationGroup:
        """Create a new recommendation_group and write it to the database."""
        self = cls()
        recommendation_group_id = self.to_database()
        return cls.from_id(recommendation_group_id)

    @classmethod
    def latest(cls) -> RecommendationGroup:
        """Fetch the lastest recommendation_group from the database."""
        records = recommendation_group.select(orderby='recommendation_group_id', ascending=False,
                                              set_index=False, limit=1)
        if records.empty:
            raise RecommendationGroupNotFound()
        else:
            return cls.from_series(records.iloc[0])

    @classmethod
    def nearest(cls, timestamp: Union[str, datetime]) -> RecommendationGroup:
        """Query for the recommendation_group nearest to `timestamp`."""
        (record, ) = execute(_NEAREST_RECOMMENDATION_GROUP, timestamp=timestamp)
        recommendation_group_id, recommendation_group_time = record
        record = cls(recommendation_group_id=recommendation_group_id,
                     recommendation_group_time=recommendation_group_time)
        return record

    @classmethod
    def remove(cls, recommendation_group_id: int) -> None:
        """Purge the recommendation_group record for `recommendation_group_id`."""
        execute(_REMOVE_RECOMMENDATION_GROUP, recommendation_group_id=recommendation_group_id)

    def embed(self) -> Dict[str, Any]:
        """Like to_dict but converts some fields to be JSON-serializable."""
        data = self.to_dict()
        data['recommendation_group_time'] = str(data['recommendation_group_time'])
        return data

    @classmethod
    def select(cls, before: Union[int, str, datetime]=None,
               after: Union[int, str, datetime]=None, limit: int=None) -> List[RecommendationGroup]:
        """Query for a listing of RecommendationGroup records based on time."""
        query = _SELECT_GROUP
        params = {}
        if before is None:
            query += _SELECT_GROUP_BEFORE_ID
            params['before_id'] = cls.latest().recommendation_group_id
        elif isinstance(before, int):
            query += _SELECT_GROUP_BEFORE_ID
            params['before_id'] = before
        else:
            query += _SELECT_GROUP_BEFORE_TIME
            params['before_time'] = before
        if after is not None:
            if isinstance(after, int):
                query += _SELECT_GROUP_AFTER_ID
                params['after_id'] = after
            else:
                query += _SELECT_GROUP_AFTER_TIME
                params['after_time'] = after

        query += _SELECT_GROUP_BY_TIME
        if limit is not None:
            query += _SELECT_GROUP_LIMIT
            params['limit'] = limit

        records = _select(query, **params)
        return [RecommendationGroup(**fields) for fields in records.to_dict(orient='records')]


class RecommendationNotFound(RecordNotFound):
    """The recommendation record was not found."""


_UPDATE_RECOMMENDATION = """\
INSERT INTO "recommendation"."recommendation" (recommendation_id, recommendation_group_id, recommendation_time,
                                               recommendation_priority, facility_id, user_id, object_id,
                                               observation_type_id, predicted_observation_id,
                                               recommendation_accepted, recommendation_rejected,
                                               recommendation_metadata)
VALUES (:recommendation_id, :recommendation_group_id, :recommendation_time,
        :recommendation_priority, :facility_id, :user_id, :object_id,
        :observation_type_id, :predicted_observation_id,
        :recommendation_accepted, :recommendation_rejected,
        :recommendation_metadata)
ON CONFLICT (recommendation_id) DO UPDATE
    SET recommendation_group_id  = excluded.recommendation_group_id,
        recommendation_time      = excluded.recommendation_time,
        recommendation_priority  = excluded.recommendation_priority,
        facility_id              = excluded.facility_id,
        user_id                  = excluded.user_id,
        object_id                = excluded.object_id,
        observation_type_id      = excluded.observation_type_id,
        predicted_observation_id = excluded.predicted_observation_id,
        recommendation_accepted  = excluded.recommendation_accepted,
        recommendation_rejected  = excluded.recommendation_rejected,
        recommendation_metadata  = excluded.recommendation_metadata;
"""


_INSERT_RECOMMENDATION = """\
INSERT INTO "recommendation"."recommendation" (recommendation_group_id, recommendation_time,
                                               recommendation_priority, facility_id, user_id, object_id,
                                               observation_type_id, predicted_observation_id,
                                               recommendation_accepted, recommendation_rejected,
                                               recommendation_metadata)
VALUES (:recommendation_group_id, :recommendation_time,
        :recommendation_priority, :facility_id, :user_id, :object_id,
        :observation_type_id, :predicted_observation_id,
        :recommendation_accepted, :recommendation_rejected,
        :recommendation_metadata)
RETURNING recommendation_id;
"""


_REMOVE_RECOMMENDATION = """\
DELETE FROM "recommendation"."recommendation"
WHERE recommendation_id = :recommendation_id;
"""


_SELECT_RECOMMENDATIONS = """\
SELECT
    recommendation.recommendation_id,
    recommendation.recommendation_group_id,
    recommendation.recommendation_time,
    recommendation.recommendation_priority,
    recommendation.recommendation_accepted,
    recommendation.recommendation_rejected,
    recommendation.recommendation_metadata,
    recommendation.user_id,

    facility.facility_id,
    facility.facility_name,
    facility.facility_limiting_magnitude,

    recommendation.object_id,
    object.object_name,
    object.object_aliases,
    object.object_ra,
    object.object_dec,
    object.object_metadata,

    recommendation.observation_type_id,
    recommendation.predicted_observation_id,
    observation.observation_value             as predicted_observation_value,
    observation_type.observation_type_name    as predicted_observation_type_name

FROM
    recommendation.recommendation as recommendation

LEFT JOIN
    profile.facility as facility
    on recommendation.facility_id = facility.facility_id

LEFT JOIN
    observation.object as object
    on recommendation.object_id = object.object_id

LEFT JOIN
    observation.observation_type as observation_type
    on recommendation.observation_type_id = observation_type.observation_type_id

LEFT JOIN
    observation.observation as observation
    on recommendation.predicted_observation_id = observation.observation_id

WHERE
"""

_SELECT_NEXT = """\
         recommendation.recommendation_group_id = :recommendation_group_id
    AND  recommendation.user_id = :user_id
    AND  recommendation.recommendation_accepted = false
    AND  recommendation.recommendation_rejected = false
"""

_SELECT_PREV = """\
         recommendation.recommendation_group_id = :recommendation_group_id
    AND  recommendation.user_id = :user_id
    AND (recommendation.recommendation_accepted = true OR
         recommendation.recommendation_rejected = true)
"""

_SELECT_BY_ID = """\
    recommendation.recommendation_id = :recommendation_id
"""

_SELECT_BY_FACILITY = """\
    AND  recommendation.facility_id = :facility_id
"""

_SELECT_BY_LIMITING_MAGNITUDE = """\
    AND  observation.observation_value < :limiting_magnitude
"""

_SELECT_ORDERED = """\
ORDER BY recommendation.recommendation_priority ASC
"""

_SELECT_LIMITED = """\
LIMIT :limit
"""


class Recommendation(Record):
    """
    A record from the "recommendation"."recommendation" table.

    Example
    -------
    >>> from refitt.database.recommendation import Recommendation
    >>> Recommendation.from_id(123)
    Recommendation(...)
    """

    _fields = ('recommendation_id', 'recommendation_group_id', 'recommendation_time', 'recommendation_priority',
               'facility_id', 'user_id', 'object_id', 'observation_type_id',
               'observation_id', 'predicted_observation_id',
               'recommendation_accepted', 'recommendation_rejected', 'recommendation_metadata')
    _masked = False

    _recommendation_id: Optional[int] = None
    _recommendation_group_id: int = None
    _recommendation_time: Optional[datetime] = None
    _recommendation_priority: int = None
    _facility_id: int = None
    _user_id: int = None
    _object_id: int = None
    _observation_type_id: int = None
    _observation_id: Optional[int] = None
    _predicted_observation_id: int = None
    _recommendation_accepted: bool = False
    _recommendation_rejected: bool = False
    _recommendation_metadata: Dict[str, Any] = {}

    _FACTORIES = {'recommendation_id': 'from_id', }

    def __init__(self, *instance, **fields) -> None:
        """Inject default values and reduce extra attributes to 'recommendation_metadata'."""
        if not fields:
            super().__init__(*instance)
        else:
            super().__init__(**{
                'recommendation_id':        fields.pop('recommendation_id', None),
                'recommendation_group_id':  fields.pop('recommendation_group_id'),
                'recommendation_time':      fields.pop('recommendation_time', datetime.utcnow()),
                'recommendation_priority':  fields.pop('recommendation_priority'),
                'facility_id':              fields.pop('facility_id'),
                'user_id':                  fields.pop('user_id'),
                'object_id':                fields.pop('object_id'),
                'observation_type_id':      fields.pop('observation_type_id'),
                'observation_id':           fields.pop('observation_id', None),
                'predicted_observation_id': fields.pop('predicted_observation_id'),
                'recommendation_accepted':  fields.pop('recommendation_accepted', False),
                'recommendation_rejected':  fields.pop('recommendation_rejected', False),
                'recommendation_metadata':  {**fields.pop('recommendation_metadata', {}), **fields}})

    @property
    def recommendation_id(self) -> Optional[int]:
        return self._recommendation_id

    @recommendation_id.setter
    def recommendation_id(self, value: int) -> None:
        _recommendation_id = None if value is None else int(value)
        if _recommendation_id is not None and _recommendation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.recommendation_id expects positive integer')
        else:
            self._recommendation_id = _recommendation_id

    @property
    def recommendation_group_id(self) -> int:
        return self._recommendation_group_id

    @recommendation_group_id.setter
    def recommendation_group_id(self, value: int) -> None:
        _recommendation_group_id = int(value)
        if _recommendation_group_id < 0:
            raise ValueError(f'{self.__class__.__name__}.recommendation_group_id expects positive integer')
        else:
            self._recommendation_group_id = _recommendation_group_id

    @property
    def recommendation_time(self) -> Optional[datetime]:
        return self._recommendation_time

    @recommendation_time.setter
    def recommendation_time(self, value: datetime) -> None:
        if value is None:
            self._recommendation_time = None
        elif isinstance(value, Timestamp):
            self._recommendation_time = value.to_pydatetime()
        elif isinstance(value, datetime):
            self._recommendation_time = value
        else:
            raise TypeError(f'{self.__class__.__name__}.recommendation_time expects {type(datetime)}')

    @property
    def recommendation_priority(self) -> int:
        return self._recommendation_priority

    @recommendation_priority.setter
    def recommendation_priority(self, value: int) -> None:
        _recommendation_priority = int(value)
        if _recommendation_priority < 0:
            raise ValueError(f'{self.__class__.__name__}.recommendation_priority expects positive integer')
        else:
            self._recommendation_priority = _recommendation_priority

    @property
    def facility_id(self) -> int:
        return self._facility_id

    @facility_id.setter
    def facility_id(self, value: int) -> None:
        _facility_id = int(value)
        if _facility_id < 0:
            raise ValueError(f'{self.__class__.__name__}.facility_id expects positive integer')
        else:
            self._facility_id = _facility_id

    @property
    def user_id(self) -> int:
        return self._user_id

    @user_id.setter
    def user_id(self, value: int) -> None:
        _user_id = int(value)
        if _user_id < 0:
            raise ValueError(f'{self.__class__.__name__}.user_id expects positive integer')
        else:
            self._user_id = _user_id

    @property
    def object_id(self) -> int:
        return self._object_id

    @object_id.setter
    def object_id(self, value: int) -> None:
        _object_id = int(value)
        if _object_id < 0:
            raise ValueError(f'{self.__class__.__name__}.object_id expects positive integer')
        else:
            self._object_id = _object_id

    @property
    def observation_type_id(self) -> int:
        return self._observation_type_id

    @observation_type_id.setter
    def observation_type_id(self, value: int) -> None:
        _observation_type_id = int(value)
        if _observation_type_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_type_id expects positive integer')
        else:
            self._observation_type_id = _observation_type_id

    @property
    def observation_id(self) -> Optional[int]:
        return self._observation_id

    @observation_id.setter
    def observation_id(self, value: int) -> None:
        _observation_id = None if value is None else int(value)
        if _observation_id is not None and _observation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.observation_id expects positive integer')
        else:
            self._observation_id = _observation_id

    @property
    def predicted_observation_id(self) -> int:
        return self._predicted_observation_id

    @predicted_observation_id.setter
    def predicted_observation_id(self, value: int) -> None:
        _predicted_observation_id = int(value)
        if _predicted_observation_id < 0:
            raise ValueError(f'{self.__class__.__name__}.predicted_observation_id expects positive integer')
        else:
            self._predicted_observation_id = _predicted_observation_id

    @property
    def recommendation_accepted(self) -> bool:
        return self._recommendation_accepted

    @recommendation_accepted.setter
    def recommendation_accepted(self, value: bool) -> None:
        if value in (True, False):
            self._recommendation_accepted = bool(value)  # NOTE: coerces `numpy.bool_`
        else:
            raise ValueError(f'{self.__class__.__name__}.recommendation_accepted expected True or False')

    @property
    def recommendation_rejected(self) -> bool:
        return self._recommendation_rejected

    @recommendation_rejected.setter
    def recommendation_rejected(self, value: bool) -> None:
        if value in (True, False):
            self._recommendation_rejected = bool(value)  # NOTE: coerces `numpy.bool_`
        else:
            raise ValueError(f'{self.__class__.__name__}.recommendation_rejected expected True or False')

    @property
    def recommendation_metadata(self) -> Dict[str, Any]:
        return self._recommendation_metadata

    @recommendation_metadata.setter
    def recommendation_metadata(self, value: Union[str, Dict[str, Any]]) -> None:
        if isinstance(value, str):
            self.recommendation_metadata = json.loads(value)  # NOTE: recursion
        else:
            _recommendation_metadata = dict(value)
            if all(isinstance(key, str) for key in _recommendation_metadata):
                self._recommendation_metadata = _recommendation_metadata
            else:
                raise ValueError(f'{self.__class__.__name__}.recommendation_metadata requires all keys to be str.')

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Recommendation:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            return super()._from_unique(table, field, value, interface)  # noqa (return type)
        except RecordNotFound as error:
            raise RecommendationNotFound(*error.args) from error

    @classmethod
    def from_id(cls, recommendation_id: int, interface: Interface = None) -> Recommendation:
        """Get recommendation record from `recommendation_id`."""
        return cls._from_unique(recommendation, 'recommendation_id', recommendation_id, interface)

    def to_database(self) -> int:
        """
        Add recommendation record to the database.
        If the recommendation_id is defined, the recommendation_time must also be defined.
        An undefined recommendation_id will be inserted as a new record and the new id returned.
        """
        data = super().to_dict()
        recommendation_id = data.pop('recommendation_id')
        data['recommendation_metadata'] = json.dumps(data['recommendation_metadata'])
        if recommendation_id:
            execute(_UPDATE_RECOMMENDATION, recommendation_id=recommendation_id, **data)
            log.info(f'updated recommendation: recommendation_id={recommendation_id}')
        else:
            ((recommendation_id, ), ) = execute(_INSERT_RECOMMENDATION, **data)
            log.info(f'added recommendation: recommendation_id={recommendation_id}')
        return recommendation_id

    @classmethod
    def remove(cls, recommendation_id: int) -> None:
        """Purge the recommendation record for `recommendation_id`."""
        execute(_REMOVE_RECOMMENDATION, recommendation_id=recommendation_id)

    def to_dict(self) -> Dict[str, Any]:
        """Dissolve record into plain dictionary. Metadata is promoted."""
        data = super().to_dict()
        metadata = data.pop('recommendation_metadata')
        return {**data, **metadata}

    def embed(self) -> Dict[str, Any]:
        """Like to_dict but converts some fields to be JSON-serializable."""
        data = self.to_dict()
        data['recommendation_time'] = str(data['recommendation_time'])
        return data

    @classmethod
    def update(cls, recommendation_id: int, **fields) -> None:
        """Update one or more `fields` for record identified."""
        old_record = cls.from_id(recommendation_id).to_dict()
        new_record = cls.from_dict({**old_record, **fields})
        new_record.to_database()

    @classmethod
    def select(cls, user_id: int, group: Union[int, str]=None, limit: int=None,
               limiting_magnitude: float=None, facility_id: int=None) -> List[Recommendation]:
        """
        Query for a list of recommendations.

        Arguments
        ---------
        user_id: int
            The user's unique identifier. See `.user.User`.
        group: int or str or None
            If None, use `RecommendationGroup.latest`. Otherwise, if an int a particular `recommendation_group_id`,
            or if str use  `RecommendationGroup.nearest` with a timestamp (str or `datetime.datetime`).
        limit: int (default: None)
            Limits the number of returned recommendations. If None, don't limit.
        limiting_magnitude: float (default: None)
            If given, filter out recommendations whose predicted magnitude is fainter than this.

        Returns
        -------
        recommendations: List[Recommendation]
            The found recommendation records.
        """
        # derive recommendation group
        group_id = group or RecommendationGroup.latest().recommendation_group_id
        if not isinstance(group_id, int):
            group_id = RecommendationGroup.nearest(group_id).recommendation_group_id

        query = _SELECT_RECOMMENDATIONS + _SELECT_NEXT
        params = {'recommendation_group_id': group_id, 'user_id': user_id}

        if facility_id:
            query += _SELECT_BY_FACILITY
            params['facility_id'] = facility_id

        if limiting_magnitude:
            query += _SELECT_BY_LIMITING_MAGNITUDE
            params['limiting_magnitude'] = limiting_magnitude

        query += _SELECT_ORDERED
        if limit:
            query += _SELECT_LIMITED
            params['limit'] = limit

        records = _select(query, **params)
        return [Recommendation(**fields) for fields in records.to_dict(orient='records')]

    @classmethod
    def select_by_id(cls, recommendation_id) -> Recommendation:
        """
        Select identified recommendation. Differs from `from_id` by doing full join.

        Arguments
        ---------
        recommendation_id: int
            The primary key to use for the lookup.

        Returns
        -------
        recommendation: Recommendation
            The found recommendation record.
        """
        query = _SELECT_RECOMMENDATIONS + _SELECT_BY_ID
        params = {'recommendation_id': recommendation_id}

        records = _select(query, **params)
        if records.empty:
            raise RecommendationNotFound(recommendation_id)

        return Recommendation.from_series(records.iloc[0])

    @classmethod
    def select_group(cls, user_id: int, group_id: int, limit: int=None) -> List[Recommendation]:
        """
        Query for a list of recommendations.

        Arguments
        ---------
        user_id: int
            The user's unique identifier. See `.user.User`.
        group_id: int
            A uniquely identified recommendation group.
        limit: int (default: None)
            Limits the number of returned recommendations. If None, don't limit.

        Returns
        -------
        recommendations: List[Recommendation]
            The found recommendation records.
        """

        query = _SELECT_RECOMMENDATIONS + _SELECT_PREV
        params = {'recommendation_group_id': group_id, 'user_id': user_id}

        query += _SELECT_ORDERED
        if limit:
            query += _SELECT_LIMITED
            params['limit'] = limit

        records = _select(query, **params)
        return [Recommendation(**fields) for fields in records.to_dict(orient='records')]
