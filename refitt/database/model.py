# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core database model definitions."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Type, Optional, Callable, TypeVar, Union

# standard libs
import re
import random
import logging
from base64 import encodebytes as base64_encode, decodebytes as base64_decode
from datetime import datetime, timedelta
from functools import lru_cache, cached_property
from dataclasses import dataclass

# external libs
from names_generator.names import LEFT, RIGHT
from sqlalchemy import Column, ForeignKey, Index, func, type_coerce, or_
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import relationship, aliased, Query
from sqlalchemy.exc import IntegrityError, NoResultFound, MultipleResultsFound
from sqlalchemy.types import Integer, BigInteger, DateTime, Float, Text, String, JSON, Boolean, LargeBinary
from sqlalchemy.schema import Sequence, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB

# internal libs
from .interface import schema, config, Session as _Session
from ..web.token import Key, Secret, Token, JWT

# public interface
__all__ = ['DatabaseError', 'NotFound', 'NotDistinct', 'AlreadyExists', 'IntegrityError',
           'ModelInterface', 'Level', 'Topic', 'Host', 'Subscriber', 'Message', 'Access',
           'User', 'Facility', 'FacilityMap', 'ObjectType', 'Object', 'SourceType',
           'Source', 'ObservationType', 'Observation', 'Alert', 'FileType', 'File',
           'RecommendationTag', 'Epoch', 'Recommendation', 'ModelType', 'Model',
           'Client', 'Session', 'tables', 'indices', 'DEFAULT_EXPIRE_TIME', 'DEFAULT_CLIENT_LEVEL', ]


# initialize module level logger
log = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Generic error with respect to the db model."""


class NotFound(NoResultFound):
    """Exception specific to no record found on lookup by unique field (e.g., `id`)."""


class NotDistinct(MultipleResultsFound):
    """Exception specific to multiple records found when only one should have been."""


class AlreadyExists(DatabaseError):
    """Exception specific to a record with unique properties already existing."""


__NT = type(None)
__VT = TypeVar('__VT', __NT, bool, int, float, str, Dict[str, Any], List[str])
__RT = Union[__VT, datetime, bytes]


def __load_datetime(value: __VT) -> Union[__VT, datetime]:
    """Passively coerce datetime formatted strings into actual datetime values."""
    if not isinstance(value, str):
        return value
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        return value


def __dump_datetime(value: __RT) -> __VT:
    """Passively coerce datetime values to formatted strings."""
    if not isinstance(value, datetime):
        return value
    else:
        return str(value)


def __load_bytes(value: __VT) -> Union[__VT, bytes]:
    """Passively coerce string lists (base64 encoded raw data)."""
    if isinstance(value, list) and all(isinstance(member, str) for member in value):
        return base64_decode('\n'.join(value).encode())
    else:
        return value


def __dump_bytes(value: __RT) -> __VT:
    """Passively coerce bytes into base64 encoded string sets."""
    if not isinstance(value, bytes):
        return value
    else:
        return base64_encode(value).decode().strip().split('\n')


__LM = Callable[[__VT], __RT]
__DM = Callable[[__RT], __VT]
__loaders: List[__LM] = [__load_datetime, __load_bytes, ]
__dumpers: List[__DM] = [__dump_datetime, __dump_bytes, ]


def __load_imp(value: __VT, filters: List[__LM]) -> __RT:
    return value if not filters else filters[0](__load_imp(value, filters[1:]))


def _load(value: __VT) -> __RT:
    """Passively coerce value types of stored record assets to db compatible types."""
    return __load_imp(value, __loaders)


def __dump_imp(value: __RT, filters: List[__DM]) -> __VT:
    return value if not filters else filters[0](__dump_imp(value, filters[1:]))


def _dump(value: __RT) -> __VT:
    """Passively coerce db types to JSON encoded types."""
    return __dump_imp(value, __dumpers)


class ModelBase:
    """Core mixin class for all models."""

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: cls
        """The table name should be the "snake_case" of the "ClassName"."""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()

    @declared_attr
    def __table_args__(cls) -> Dict[str, Any]:  # noqa: cls
        """Common table attributes."""
        return {'schema': schema, }

    columns: Dict[str, type] = {}
    relationships: Dict[str, Type[ModelInterface]] = {}

    def __repr__(self) -> str:
        """String representation of record."""
        return (f'<{self.__class__.__name__}(' +
                ', '.join([f'{name}={repr(getattr(self, name))}' for name in self.columns]) +
                ')>')

    def to_tuple(self) -> tuple:
        """Convert fields into standard tuple."""
        return tuple([getattr(self, name) for name in self.columns])

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {name: getattr(self, name) for name in self.columns}

    @classmethod
    def from_dict(cls: Type[ModelInterface], data: Dict[str, Any]) -> ModelInterface:
        """Build record from existing dictionary."""
        return cls(**data)

    @classmethod
    def new(cls: Type[ModelInterface], **fields) -> ModelInterface:
        """Create new instance of the model with default fields."""
        return cls(**fields)

    @classmethod
    def from_json(cls: Type[ModelInterface], data: Dict[str, __VT]) -> ModelInterface:
        """Build record from JSON data (already loaded as dictionary)."""
        return cls.from_dict({k: _load(v) for k, v in data.items()})

    def to_json(self, pop: List[str] = None, join: bool = False) -> Dict[str, __VT]:
        """Convert record values into JSON formatted types."""
        data = {k: _dump(v) for k, v in self.to_dict().items()}
        if pop is not None:
            for field in pop:
                data.pop(field)
        if join is True:
            for name in self.relationships:
                relation = getattr(self, name)
                if isinstance(relation, list):
                    data[name] = [record.to_json(join=True) for record in relation]
                elif isinstance(relation, ModelInterface):
                    data[name] = relation.to_json(join=True)
                elif relation is None:
                    pass
                else:
                    raise AttributeError(f'Unexpected {relation.__class__.__name__}({relation}) for '
                                         f'{self.__class__.__name__}.{name}')
        return data

    @classmethod
    def from_id(cls: Type[ModelInterface], id: int, session: _Session = None) -> ModelInterface:
        """Query using unique `id`."""
        try:
            if hasattr(cls, 'id'):
                session = session or _Session()
                return session.query(cls).filter(cls.id == id).one()
            else:
                raise AttributeError(f'{cls} has no `id` attribute')
        except NoResultFound as error:
            raise cls.NotFound(f'No {cls.__tablename__} with id={id}') from error

    @classmethod
    def add(cls: Type[ModelInterface], data: dict, session: _Session = None) -> ModelInterface:
        """Add record from existing `data`, return constructed record."""
        record, = cls.add_all([data, ], session=session)
        return record

    @classmethod
    def add_all(cls: Type[ModelInterface], data: List[dict], session: _Session = None) -> List[ModelInterface]:
        """Add list of new records to the database and return constructed records."""
        session = session or _Session()
        try:
            records = [cls.from_dict(record) for record in data]
            session.add_all(records)
            session.commit()
            for record in records:
                log.info(f'Added {cls.__tablename__} ({record.id})')
            return records
        except (IntegrityError, DatabaseError):
            session.rollback()
            raise

    @classmethod
    def update(cls: Type[ModelInterface], id: int, **data) -> ModelInterface:
        """Update named attributes of specified record."""
        try:
            record = cls.from_id(id)
            for field, value in data.items():
                if field in cls.columns:
                    setattr(record, field, value)
                else:
                    record.data = {**record.data, field: value}
            _Session.commit()
            log.info(f'Updated {cls.__tablename__} ({id})')
            return record
        except (IntegrityError, DatabaseError):
            _Session.rollback()
            raise

    @classmethod
    def delete(cls: Type[ModelInterface], id: int) -> None:
        """Delete existing record with `id`."""
        record = cls.from_id(id)
        _Session.delete(record)
        _Session.commit()
        log.info(f'Deleted {cls.__tablename__} ({id})')

    @classmethod
    def count(cls) -> int:
        """Count of records in table."""
        return cls.query().count()

    @classmethod
    def query(cls: Type[ModelInterface]) -> Query:
        return _Session.query(cls)


# declarative base inherits common interface
ModelInterface = declarative_base(cls=ModelBase)


class User(ModelInterface):
    """User profiles store attributes about a participating human observer."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    first_name = Column('first_name', Text(), nullable=False)
    last_name = Column('last_name', Text(), nullable=False)
    email = Column('email', Text(), unique=True, nullable=False)
    alias = Column('alias', Text(), unique=True, nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    columns = {
        'id': int,
        'first_name': str,
        'last_name': str,
        'email': str,
        'alias': str,
        'data': dict
    }

    class NotFound(NotFound):
        """NotFound exception specific to User."""

    @classmethod
    def from_email(cls, address: str, session: _Session = None) -> User:
        """Query by unique email `address`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.email == address).one()
        except NoResultFound as error:
            raise User.NotFound(f'No user with email={address}') from error

    @classmethod
    def from_alias(cls, alias: str, session: _Session = None) -> User:
        """Query by unique `alias`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.alias == alias).one()
        except NoResultFound as error:
            raise User.NotFound(f'No user with alias={alias}') from error

    def facilities(self, session: _Session = None) -> List[Facility]:
        """Facilities associated with this user (queries `facility_map`)."""
        session = session or _Session()
        return (session.query(Facility).join(FacilityMap).filter(FacilityMap.user_id == self.id)
                .order_by(FacilityMap.facility_id).all())

    def add_facility(self, facility_id: int, session: _Session = None) -> None:
        """Associate `facility_id` with this user."""
        session = session or _Session()
        facility = Facility.from_id(facility_id, session)  # checks for Facility.NotFound
        try:
            session.query(FacilityMap).filter(FacilityMap.user_id == self.id,
                                              FacilityMap.facility_id == facility_id).one()
        except NoResultFound:
            session.add(FacilityMap(user_id=self.id, facility_id=facility.id))
            session.commit()
            log.info(f'Associated facility ({facility.id}) with user ({self.id})')

    def delete_facility(self, facility_id: int) -> None:
        """Dissociate facility with this user."""
        session = _Session()
        facility = Facility.from_id(facility_id, session)  # checks for Facility.NotFound
        for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == self.id,
                                                         FacilityMap.facility_id == facility.id):
            session.delete(mapping)
            session.commit()
            log.info(f'Dissociated facility ({facility.id}) from user ({self.id})')

    @classmethod
    def delete(cls, user_id: int, session: _Session = None) -> None:
        """Cascade delete to Client, Session, and FacilityMap."""
        session = session or _Session()
        user = cls.from_id(user_id)
        for client in session.query(Client).filter(Client.user_id == user_id):
            for _session in session.query(Session).filter(Session.client_id == client.id):
                session.delete(_session)
                session.commit()
                log.info(f'Deleted session for user ({user_id})')
            session.delete(client)
            session.commit()
            log.info(f'Deleted client for user ({user_id})')
        for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == user_id):
            session.delete(mapping)
            session.commit()
            log.info(f'Dissociated facility ({mapping.facility_id}) from user ({user_id})')
        session.delete(user)
        session.commit()
        log.info(f'Deleted user ({user_id})')


class Facility(ModelInterface):
    """Facility profiles store characteristics about a telescope and it's instruments."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    latitude = Column('latitude', Float(), nullable=False)
    longitude = Column('longitude', Float(), nullable=False)
    elevation = Column('elevation', Float(), nullable=False)
    limiting_magnitude = Column('limiting_magnitude', Float(), nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    columns = {
        'id': int,
        'name': str,
        'latitude': float,
        'longitude': float,
        'elevation': float,
        'limiting_magnitude': float,
        'data': dict
    }

    class NotFound(NotFound):
        """NotFound exception specific to Facility."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Facility:
        """Query by unique `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Facility.NotFound(f'No facility with name={name}') from error

    def users(self, session: _Session = None) -> List[User]:
        """Users associated with this facility (queries `facility_map`)."""
        session = session or _Session()
        return (session.query(User).join(FacilityMap).filter(FacilityMap.facility_id == self.id)
                .order_by(FacilityMap.user_id).all())

    def add_user(self, user_id: int) -> None:
        """Associate user with this facility."""
        session = _Session()
        user = User.from_id(user_id, session)  # checks for User.NotFound
        try:
            session.query(FacilityMap).filter(FacilityMap.user_id == user_id,
                                              FacilityMap.facility_id == self.id).one()
        except NoResultFound:
            session.add(FacilityMap(user_id=user.id, facility_id=self.id))
            session.commit()
            log.info(f'Associated facility ({self.id}) with user ({user.id})')

    def delete_user(self, user_id: int) -> None:
        """Dissociate `user` with this facility."""
        session = _Session()
        user = User.from_id(user_id, session)  # checks for User.NotFound
        for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == user.id,
                                                         FacilityMap.facility_id == self.id):
            session.delete(mapping)
            session.commit()
            log.info(f'Dissociated facility ({self.id}) from user ({user.id})')

    @classmethod
    def delete(cls, facility_id: int, session: _Session = None) -> None:
        """Cascade delete to FacilityMap."""
        session = session or _Session()
        facility = cls.from_id(facility_id)
        for mapping in session.query(FacilityMap).filter(FacilityMap.facility_id == facility_id):
            session.delete(mapping)
            session.commit()
            log.info(f'Dissociated facility ({facility_id}) from user ({mapping.user_id})')
        session.delete(facility)
        session.commit()
        log.info(f'Deleted facility ({facility_id})')


class FacilityMap(ModelInterface):
    """Mapping table between users and facilities."""

    user_id = Column('user_id', Integer(), ForeignKey(User.id, ondelete='cascade'),
                     primary_key=True, nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id, ondelete='cascade'),
                         primary_key=True, nullable=False)

    columns = {
        'user_id': int,
        'facility_id': int
    }

    @classmethod
    def from_id(cls, id: int, session: _Session = None) -> FacilityMap:
        raise NotImplementedError()

    @classmethod
    def add(cls, data: dict, session: _Session = None) -> Optional[int]:
        raise NotImplementedError()

    @classmethod
    def delete(cls, id: int, session: _Session = None) -> None:
        raise NotImplementedError()

    @classmethod
    def update(cls, id: int, session: _Session = None, **data) -> None:
        raise NotImplementedError()


# New credentials will be initialized with this level unless otherwise specified
DEFAULT_CLIENT_LEVEL: int = 10


class Client(ModelInterface):
    """Client stores user authorization and authentication."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    user_id = Column('user_id', Integer(), ForeignKey(User.id), unique=True, nullable=False)
    level = Column('level', Integer(), nullable=False)
    key = Column('key', String(16), unique=True, nullable=False)
    secret = Column('secret', String(64), nullable=False)
    valid = Column('valid', Boolean(), nullable=False)
    created = Column('created', DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship(User, backref='client')

    relationships = {'user': User}
    columns = {
        'id': int,
        'user_id': int,
        'level': int,
        'key': str,
        'secret': str,
        'valid': bool,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Client."""

    @classmethod
    def from_key(cls, key: str, session: _Session = None) -> Client:
        """Query by unique `key`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.key == key).one()
        except NoResultFound as error:
            raise Client.NotFound(f'No client with key={key}') from error

    @classmethod
    def from_user(cls, user_id: int, session: _Session = None) -> Client:
        """Query by unique `user_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.user_id == user_id).one()
        except NoResultFound as error:
            raise Client.NotFound(f'No client with user_id={user_id}') from error

    @classmethod
    def new(cls, user_id: int, level: int = DEFAULT_CLIENT_LEVEL) -> Tuple[Key, Secret, Client]:
        """Create client credentials for `user_id` with `level`."""
        session = _Session()
        user = User.from_id(user_id, session)
        key, secret = Key.generate(), Secret.generate()
        client = Client(user_id=user.id, level=level, key=key.value, secret=secret.hashed().value, valid=True)
        session.add(client)
        session.commit()
        log.info(f'Added client for user ({user.id})')
        return key, secret, client

    @classmethod
    def new_secret(cls, user_id: int) -> Tuple[Key, Secret]:
        """Generate a new secret (store the hashed value)."""
        session = _Session()
        client = Client.from_user(user_id, session)
        secret = Secret.generate()
        client.secret = secret.hashed().value
        session.commit()
        log.info(f'Updated client secret for user ({client.user_id})')
        return Key(client.key), secret

    @classmethod
    def new_key(cls, user_id: int) -> Tuple[Key, Secret]:
        """Generate a new key and secret (store the hashed value)."""
        session = _Session()
        client = Client.from_user(user_id, session)
        key, secret = Key.generate(), Secret.generate()
        client.key = key.value
        client.secret = secret.hashed().value
        session.commit()
        log.info(f'Updated client key and secret for user ({client.user_id})')
        return key, secret


# New session tokens if not otherwise requested will have the following lifetime (seconds)
DEFAULT_EXPIRE_TIME: int = 900  # i.e., 15 minutes


class Session(ModelInterface):
    """Session stores hashed token with claim details."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    client_id = Column('client_id', Integer(), ForeignKey(Client.id, ondelete='cascade'), unique=True, nullable=False)
    expires = Column('expires', DateTime(timezone=True), nullable=True)  # NULL is no-expiration!
    token = Column('token', String(64), nullable=False)
    created = Column('created', DateTime(timezone=True), nullable=False, server_default=func.now())

    client = relationship(Client, backref='session')

    relationships = {'client': Client}
    columns = {
        'id': int,
        'client_id': int,
        'expires': datetime,
        'token': str,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Session."""

    @classmethod
    def from_client(cls, client_id: int, session: _Session = None) -> Session:
        """Query by unique client `id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.client_id == client_id).one()
        except NoResultFound as error:
            raise Session.NotFound(f'No session with client_id={client_id}') from error

    @classmethod
    def new(cls, user_id: int, expires: Optional[Union[float, timedelta]] = DEFAULT_EXPIRE_TIME) -> JWT:
        """Create new session for `user`."""
        session = _Session()
        client = Client.from_user(user_id, session)
        if expires is None:
            exp = None
            log.warning('Creating session token with no expiration time')
        else:
            exp = expires if isinstance(expires, timedelta) else timedelta(seconds=expires)
        jwt = JWT(sub=client.id, exp=exp)
        token = Token(jwt.encrypt()).hashed().value
        try:
            old = Session.from_client(client.id, session)
            old.expires = jwt.exp
            old.token = token
            old.created = datetime.now()
        except Session.NotFound:
            new = Session(client_id=client.id, expires=jwt.exp, token=token)
            session.add(new)
        session.commit()
        log.info(f'Created session for user ({user_id})')
        return jwt


class ObjectType(ModelInterface):
    """Object types (e.g., 'SNIa')."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ObjectType."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ObjectType:
        """Query by unique object_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise ObjectType.NotFound(f'No object_type with name={name}') from error

    @classmethod
    def get_or_create(cls, name: str, session: _Session = None) -> ObjectType:
        """Get or create object_type for a given `name`."""
        session = session or _Session()
        try:
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound:
            return cls.add({'name': name, 'description': f'{name} (automatically created)'}, session=session)


# Object name provider pattern matching
OBJECT_NAMING_PATTERNS: Dict[str, re.Pattern] = {
    'ztf': re.compile(r'ZTF.*'),
    'iau': re.compile(r'20[2-3][0-9][a-zA-Z]+'),
    'antares': re.compile(r'ANT.*'),
    'tag': re.compile(r'[a-z]+_[a-z]+_[a-z]'),
}


class Object(ModelInterface):
    """An astronomical object defines names, position, and other attributes."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ObjectType.id), nullable=True)
    pred_type_id = Column('pred_type_id', Integer(), ForeignKey(ObjectType.id), nullable=True)
    aliases = Column('aliases', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})
    ra = Column('ra', Float(), nullable=False)
    dec = Column('dec', Float(), nullable=False)
    redshift = Column('redshift', Float(), nullable=True)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    type = relationship(ObjectType, foreign_keys=[type_id, ])

    relationships = {'type': ObjectType}
    columns = {
        'id': int,
        'type_id': int,
        'pred_type_id': int,
        'aliases': dict,
        'ra': float,
        'dec': float,
        'redshift': float,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to Object."""

    @classmethod
    def from_alias(cls, session: _Session = None, **alias: str) -> Object:
        """Query by named field in `aliases`."""
        if len(alias) == 1:
            (provider, name), = alias.items()
        else:
            raise AttributeError(f'Expected single named alias')
        try:
            session = session or _Session()
            return session.query(Object).filter(Object.aliases[provider] == type_coerce(name, JSON)).one()
        except NoResultFound as error:
            raise Object.NotFound(f'No object with alias {provider}={name}') from error
        except MultipleResultsFound as error:
            raise NotDistinct(f'Multiple objects with alias {provider}={name}') from error

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Object:
        """Smart detection of alias by name syntax."""
        for provider, pattern in OBJECT_NAMING_PATTERNS.items():
            if pattern.match(name):
                return cls.from_alias(**{provider: name, 'session': session})
        else:
            raise Object.NotFound(f'Unrecognized name pattern \'{name}\'')

    @classmethod
    def add_alias(cls, object_id: int, session: _Session = None, **aliases: str) -> None:
        """Add alias(es) to the given object."""
        session = session or _Session()
        try:
            obj = Object.from_id(object_id, session)
            for provider, name in aliases.items():
                try:
                    existing = Object.from_alias(session=session, **{provider: name, })
                    if existing.id != object_id:
                        raise AlreadyExists(f'Object with alias {provider}={name} already exists')
                except Object.NotFound:
                    obj.aliases = {**obj.aliases, provider: name}
            session.commit()
        except (IntegrityError, AlreadyExists):
            session.rollback()
            raise


class ObservationType(ModelInterface):
    """Observation types (e.g., 'g-ztf')."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    units = Column('units', Text(), nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'units': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ObservationType."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ObservationType:
        """Query by unique observation_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise ObservationType.NotFound(f'No observation_type with name={name}') from error


class SourceType(ModelInterface):
    """Source types (e.g., 'broker')."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to SourceType."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> SourceType:
        """Query by unique source_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise SourceType.NotFound(f'No source_type with name={name}') from error


class Source(ModelInterface):
    """Source table."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(SourceType.id), nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id), nullable=True)
    user_id = Column('user_id', Integer(), ForeignKey(User.id), nullable=True)
    name = Column('name', Text(), unique=True, nullable=False)
    description = Column('description', Text(), nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    type = relationship(SourceType, backref='source')
    facility = relationship(Facility, backref='source')
    user = relationship(User, backref='source')

    relationships = {'type': SourceType, 'facility': Facility, 'user': User}
    columns = {
        'id': int,
        'type_id': int,
        'facility_id': int,
        'user_id': int,
        'name': str,
        'description': str,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to Source."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Source:
        """Query by unique source `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Source.NotFound(f'No source with name={name}') from error

    @classmethod
    def with_facility(cls, facility_id: int, session: _Session = None) -> Source:
        """Query by unique source `facility_id`."""
        session = session or _Session()
        return session.query(cls).filter(cls.facility_id == facility_id).all()

    @classmethod
    def with_user(cls, user_id: int, session: _Session = None) -> Source:
        """Query by unique source `user_id`."""
        session = session or _Session()
        return session.query(cls).filter(cls.user_id == user_id).all()

    @classmethod
    def get_or_create(cls, user_id: int, facility_id: int) -> Source:
        """Fetch or create a new source for a `user_id`, `facility_id` pair."""
        user = User.from_id(user_id)
        facility = Facility.from_id(facility_id)
        user_name = user.alias.lower().replace(' ', '_').replace('-', '_')
        facility_name = facility.name.lower().replace(' ', '_').replace('-', '_')
        source_name = f'{user_name}_{facility_name}'
        try:
            FacilityMap.query().filter_by(user_id=user_id, facility_id=facility_id).one()
        except NoResultFound:
            log.warning(f'Facility ({facility_id}) not associated with user ({user_id})')
        try:
            return Source.from_name(source_name)
        except Source.NotFound:
            return Source.add({'type_id': SourceType.from_name('observer').id,
                               'user_id': user_id, 'facility_id': facility_id, 'name': source_name,
                               'description': f'Observer (alias={user.alias}, facility={facility.name})'})


class Epoch(ModelInterface):
    """Epoch table."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    created = Column('created', DateTime(timezone=True), nullable=False, server_default=func.now())

    columns = {
        'id': int,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Epoch."""

    @classmethod
    def new(cls, session: _Session = None) -> Epoch:
        """Create and return a new epoch."""
        return cls.add({}, session=session)

    @classmethod
    def latest(cls, session: _Session = None) -> Epoch:
        """Get the most recent epoch."""
        session = session or _Session()
        return session.query(cls).order_by(cls.id.desc()).first()

    @classmethod
    def select(cls, limit: int, offset: int = 0) -> List[Epoch]:
        """Select a range of epochs."""
        return cls.query().order_by(cls.id.desc()).filter(cls.id <= cls.latest().id - offset).limit(limit).all()


class Observation(ModelInterface):
    """Observation table."""

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    epoch_id = Column('epoch_id', Integer(), ForeignKey(Epoch.id), nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ObservationType.id), nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), nullable=False)
    source_id = Column('source_id', Integer(), ForeignKey(Source.id), nullable=False)
    value = Column('value', Float(), nullable=True)  # NOTE: null value is 'provisional' observation
    error = Column('error', Float(), nullable=True)
    time = Column('time', DateTime(timezone=True), nullable=False)
    recorded = Column('recorded', DateTime(timezone=True), nullable=False, server_default=func.now())

    epoch = relationship(Epoch, backref='observation')
    type = relationship(ObservationType, backref='observation')
    object = relationship(Object, backref='observation')
    source = relationship(Source, backref='observation')

    relationships = {'epoch': Epoch, 'type': ObservationType, 'object': Object, 'source': Source}
    columns = {
        'id': int,
        'epoch_id': int,
        'type_id': int,
        'object_id': int,
        'source_id': int,
        'value': float,
        'error': float,
        'time': datetime,
        'recorded': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Observation."""

    @classmethod
    def with_object(cls, object_id: int, session: _Session = None) -> List[Observation]:
        """All observations with `object_id`."""
        session = session or _Session()
        return session.query(cls).order_by(cls.id).filter(cls.object_id == object_id).all()

    @classmethod
    def with_source(cls, source_id: int, session: _Session = None) -> List[Observation]:
        """All observations with `source_id`."""
        session = session or _Session()
        return session.query(cls).order_by(cls.id).filter(cls.source_id == source_id).all()

    @cached_property
    def models(self) -> List[Model]:
        """Models associated with the current observation and 'epoch_id'."""
        return (
            Model.query()
            .order_by(Model.type_id)
            .filter(Model.observation_id == self.id)
            .filter(Model.epoch_id == self.epoch_id)
            .all()
        )


# indices for observation table
observation_object_index = Index('observation_object_index', Observation.object_id)
observation_source_object_index = Index('observation_source_object_index', Observation.source_id, Observation.object_id)
observation_time_index = Index('observation_time_index', Observation.time)
observation_recorded_index = Index('observation_recorded_index', Observation.recorded)


class Alert(ModelInterface):
    """Alert table."""

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    epoch_id = Column('epoch_id', Integer(), ForeignKey(Epoch.id), nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), unique=True, nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False)

    epoch = relationship(Epoch, backref='alert')
    observation = relationship(Observation, backref='alert')

    relationships = {'epoch': Epoch, 'observation': Observation, }
    columns = {
        'id': int,
        'epoch_id': int,
        'observation_id': int,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to Alert."""

    @classmethod
    def from_observation(cls, observation_id: int, session: _Session = None) -> Alert:
        """Query by unique alert `observation_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.observation_id == observation_id).one()
        except NoResultFound as error:
            raise Alert.NotFound(f'No alert with observation_id={observation_id}') from error


class FileType(ModelInterface):
    """File type table."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to FileType."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> FileType:
        """Query by unique file_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise FileType.NotFound(f'No file_type with name={name}') from error

    @classmethod
    def all_names(cls) -> List[str]:
        """All names of currently available file_type.name values."""
        return [file_type.name for file_type in cls.query().all()]


class File(ModelInterface):
    """File table."""

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    epoch_id = Column('epoch_id', Integer(), ForeignKey(Epoch.id), nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), unique=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(FileType.id), nullable=False)
    data = Column('data', LargeBinary(), nullable=False)

    epoch = relationship(Epoch, backref='file')
    type = relationship(FileType, backref='file')
    observation = relationship(Observation, backref='file')

    relationships = {'epoch': Epoch, 'type': FileType, 'observation': Observation, }
    columns = {
        'id': int,
        'epoch_id': int,
        'observation_id': int,
        'type_id': int,
        'data': bytes,
    }

    class NotFound(NotFound):
        """NotFound exception specific to File."""

    @classmethod
    def from_observation(cls, observation_id: int, session: _Session = None) -> File:
        """Query by unique file `observation_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.observation_id == observation_id).one()
        except NoResultFound as error:
            raise File.NotFound(f'No file with observation_id={observation_id}') from error


class ModelType(ModelInterface):
    """Model type table."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ModelType."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ModelType:
        """Query by unique model_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise ModelType.NotFound(f'No model_type with name={name}') from error


@dataclass
class ModelInfo:
    """Model information without the data payload."""
    id: int
    epoch_id: int
    type_id: int
    observation_id: int

    def to_json(self) -> Dict[str, int]:
        """Convert to dictionary (consistent with ModelInterface)."""
        return {'id': self.id, 'epoch_id': self.epoch_id,
                'type_id': self.type_id, 'observation_id': self.observation_id}


class Model(ModelInterface):
    """Model table."""

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    epoch_id = Column('epoch_id', Integer(), ForeignKey(Epoch.id), nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ModelType.id), nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False)

    epoch = relationship(Epoch, backref='model')
    type = relationship(ModelType, backref='model')
    observation = relationship(Observation, backref='model')

    relationships = {'epoch': Epoch, 'type': ModelType, 'observation': Observation, }
    columns = {
        'id': int,
        'epoch_id': int,
        'type_id': int,
        'observation_id': int,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to Model."""


class RecommendationTag(ModelInterface):
    """Recommendation tag table."""

    id = Column('id', Integer(), primary_key=True, nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), unique=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=True)

    object = relationship(Object, backref='recommendation_tag')

    relationships = {'object': Object, }
    columns = {
        'id': int,
        'object_id': int,
        'name': str,
    }

    class NotFound(NotFound):
        """NotFound exception specific to RecommendationTag."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> RecommendationTag:
        """Query by unique recommendation_tag `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise RecommendationTag.NotFound(f'No recommendation_tag with name={name}') from error

    @classmethod
    def get_or_create(cls, object_id: int, session: _Session = None) -> RecommendationTag:
        """Get or create recommendation tag for `object_id`."""
        session = session or _Session()
        try:
            return session.query(cls).filter(cls.object_id == object_id).one()
        except NoResultFound:
            return cls.new(object_id, session=session)
    
    @classmethod
    def new(cls, object_id: int, session: _Session = None) -> RecommendationTag:
        """Create a new recommendation tag for `object_id`."""
        session = session or _Session()
        try:
            # NOTE: The tag.name is Nullable at first because we have to first commit
            # the tag to get it's tag.id because that's what we use to slice into the names list.
            tag = cls.add({'object_id': object_id}, session=session)
            tag.name = cls.get_name(tag.id)
            session.commit()
            Object.add_alias(object_id, tag=tag.name, session=session)
            return tag
        except Exception:
            session.rollback()
            raise

    # global stored value does not change
    COUNT: int = len(LEFT) * len(LEFT) * len(RIGHT)

    @staticmethod
    @lru_cache(maxsize=1)
    def build_names(seed: int = 1) -> List[str]:
        """Reproducibly generate shuffled list of names."""
        names = [f'{a}_{b}_{c}' for a in LEFT for b in LEFT for c in RIGHT]
        random.seed(seed)
        random.shuffle(names)
        return names

    @classmethod
    def get_name(cls, tag_id: int) -> str:
        """Slice into ordered sequence of names."""
        names = cls.build_names()
        return names[tag_id]  # NOTE: will fail when we pass ~2.5M recommended objects


class Recommendation(ModelInterface):
    """Recommendation table."""

    id = Column('id', BigInteger().with_variant(Integer(), 'sqlite'), primary_key=True, nullable=False)
    epoch_id = Column('epoch_id', Integer(), ForeignKey(Epoch.id), nullable=False)
    tag_id = Column('tag_id', Integer(), ForeignKey(RecommendationTag.id), nullable=False)
    time = Column('time', DateTime(timezone=True), nullable=False, server_default=func.now())
    priority = Column('priority', Integer(), nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id), nullable=False)
    user_id = Column('user_id', Integer(), ForeignKey(User.id), nullable=False)
    predicted_observation_id = Column('predicted_observation_id', BigInteger().with_variant(Integer(), 'sqlite'),
                                      ForeignKey(Observation.id), nullable=True)
    observation_id = Column('observation_id', BigInteger().with_variant(Integer(), 'sqlite'),
                            ForeignKey(Observation.id), nullable=True)
    accepted = Column('accepted', Boolean(), nullable=False, default=False)
    rejected = Column('rejected', Boolean(), nullable=False, default=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    epoch = relationship(Epoch, backref='recommendation')
    tag = relationship(RecommendationTag, backref='recommendation')
    user = relationship(User, backref='recommendation')
    facility = relationship(Facility, backref='recommendation')
    object = relationship(Object, backref='recommendation')
    predicted = relationship(Observation, foreign_keys=[predicted_observation_id, ])
    observed = relationship(Observation, foreign_keys=[observation_id, ])

    relationships = {'epoch': Epoch, 'tag': RecommendationTag,
                     'user': User, 'facility': Facility, 'object': Object,
                     'predicted': Observation, 'observed': Observation, }
    columns = {
        'id': int,
        'epoch_id': int,
        'tag_id': int,
        'time': datetime,
        'priority': int,
        'object_id': int,
        'facility_id': int,
        'user_id': int,
        'predicted_observation_id': int,
        'observation_id': int,
        'accepted': bool,
        'rejected': bool,
        'data': dict
    }

    class NotFound(NotFound):
        """NotFound exception specific to Recommendation."""

    @cached_property
    def model_info(self) -> List[ModelInfo]:
        """Listing of available models for this recommendation without the data itself."""
        return [
            ModelInfo(id, epoch_id, type_id, observation_id)
            for id, epoch_id, type_id, observation_id in
            _Session.query(Model.id, Model.epoch_id, Model.type_id, Model.observation_id)
                .order_by(Model.type_id)
                .filter(Model.observation_id == self.predicted_observation_id)
                .filter(Model.epoch_id == self.epoch_id)
                .all()
        ]

    @cached_property
    def models(self) -> List[Model]:
        """Models associated with the 'predicted_observation_id' and 'epoch_id'."""
        return (
            Model.query()
            .order_by(Model.type_id)
            .filter(Model.observation_id == self.predicted_observation_id)
            .filter(Model.epoch_id == self.epoch_id)
            .all()
        )

    @classmethod
    def for_user(cls, user_id: int, epoch_id: int = None, session: _Session = None) -> List[Recommendation]:
        """Select recommendations for the given user and group."""
        session = session or _Session()
        epoch_id = epoch_id or Epoch.latest(session).id
        return (session.query(cls).order_by(cls.priority)
                .filter(cls.epoch_id == epoch_id, cls.user_id == user_id)).all()

    @classmethod
    def next(cls, user_id: int, epoch_id: int = None, limit: int = None,
             facility_id: int = None, limiting_magnitude: float = None) -> List[Recommendation]:
        """
        Select next recommendation(s) for the given user and group, in priority order,
        that has neither been 'accepted' nor 'rejected', up to some `limit`.

        If `facility_id` is provided, only recommendations for the given facility are returned.
        If `limiting_magnitude` is provided, only recommendations with a 'predicted' magnitude
        brighter than this value are returned.
        """
        session = _Session()
        predicted = aliased(Observation)
        query = session.query(cls).join(predicted, cls.predicted_observation_id == predicted.id)
        query = query.order_by(cls.priority)
        query = query.filter(cls.user_id == user_id)
        query = query.filter(cls.epoch_id == (epoch_id or Epoch.latest(session).id))
        query = query.filter(cls.accepted.is_(False)).filter(cls.rejected.is_(False))
        if facility_id is not None:
            query = query.filter(cls.facility_id == facility_id)
        if limiting_magnitude is not None:
            query = query.filter(predicted.value <= limiting_magnitude)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def history(cls, user_id: int, epoch_id: int) -> List[Recommendation]:
        """
        Select previous recommendations that the user has either affirmatively
        accepted OR rejected.
        """
        return (cls.query().order_by(cls.id)
                .filter(cls.user_id == user_id).filter(cls.epoch_id == epoch_id)
                .filter(or_(cls.accepted.is_(True), cls.rejected.is_(True)))).all()


# indices for recommendation table
recommendation_object_index = Index('recommendation_object_index', Recommendation.object_id)
recommendation_user_facility_index = Index('recommendation_user_facility_index',
                                           Recommendation.user_id, Recommendation.facility_id)
recommendation_epoch_user_index = Index('recommendation_epoch_user_index',
                                        Recommendation.epoch_id, Recommendation.user_id)


# ----------------------------------------------------------------------------------------------
# Re-implementation of StreamKit models
# We conform to the database schema but re-define under a common ModelInterface


class Level(ModelInterface):
    """A level relates a name and its identifier."""

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String(), unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Level."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Level:
        """Query by unique level `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Level.NotFound(f'No level with name={name}') from error


class Topic(ModelInterface):
    """A topic relates a name and its identifier."""

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String(), unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Topic."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Topic:
        """Query by unique topic `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Topic.NotFound(f'No topic with name={name}') from error


class Host(ModelInterface):
    """A host relates a name and its identifier."""

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String(), unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Host."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Host:
        """Query by unique host `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Host.NotFound(f'No host with name={name}') from error


class Message(ModelInterface):
    """A message joins topic, level, and host, with timestamp and an identifier for the message."""

    id = Column('id', BigInteger().with_variant(Integer(), 'sqlite'), primary_key=True)
    time = Column('time', DateTime(timezone=True), nullable=False)
    topic_id = Column('topic_id', Integer(), ForeignKey(Topic.id), nullable=False)
    level_id = Column('level_id', Integer(), ForeignKey(Level.id), nullable=False)
    host_id = Column('host_id', Integer(), ForeignKey(Host.id), nullable=False)
    text = Column('text', String(), nullable=False)

    # Note: conditionally redefine for time-based partitioning
    if config.provider in ('timescale', ):
        # The primary key is (`time`, `topic_id`) NOT `id`.
        # This is weird but important for automatic hyper-table partitioning
        # on the `time` values for TimeScaleDB (PostgreSQL).
        id = Column('id', BigInteger(),
                    Sequence('message_id_seq', start=1, increment=1, schema=schema),
                    CheckConstraint('id > 0', name='message_id_check'), nullable=False)
        time = Column('time', DateTime(timezone=True), nullable=False, primary_key=True)
        topic_id = Column('topic_id', Integer(), nullable=False, primary_key=True)

    topic = relationship('Topic', backref='message')
    level = relationship('Level', backref='message')
    host = relationship('Host', backref='message')

    relationships = {'topic': Topic, 'level': Level, 'host': Host}
    columns = {
        'id': int,
        'time': datetime,
        'topic_id': int,
        'level_id': int,
        'host_id': int,
        'text': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Message."""


if config.provider in ('timescale', ):
    # NOTE: we use time-topic PK and need to index ID
    message_id_index = Index('message_id_index', Message.id)
    message_time_topic_index = None
else:
    message_id_index = None
    message_time_topic_index = Index('message_time_topic_index', Message.time, Message.topic_id)


class Subscriber(ModelInterface):
    """A subscriber relates a name and its identifier."""

    id = Column('id', Integer(), primary_key=True)
    name = Column('name', String(), unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Subscriber."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Subscriber:
        """Query by unique subscriber `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Subscriber.NotFound(f'No subscriber with name={name}') from error


class Access(ModelInterface):
    """Access tracks the last message received on a given topic for a given subscriber."""

    subscriber_id = Column('subscriber_id', Integer(), ForeignKey(Subscriber.id), nullable=False, primary_key=True)
    topic_id = Column('topic_id', Integer(), ForeignKey(Topic.id), nullable=False, primary_key=True)
    time = Column('time', DateTime(timezone=True), nullable=False)

    subscriber = relationship('Subscriber', backref='access')
    topic = relationship('Topic', backref='access')

    relationships = {'subscriber': Subscriber, 'topic': Topic}
    columns = {
        'subscriber_id': int,
        'topic_id': int,
        'time': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Access."""


# ----------------------------------------------------------------------------------------------


# global registry of tables
tables: Dict[str, ModelInterface] = {
    'facility': Facility,
    'user': User,
    'facility_map': FacilityMap,
    'client': Client,
    'session': Session,
    'object_type': ObjectType,
    'object': Object,
    'observation_type': ObservationType,
    'source_type': SourceType,
    'source': Source,
    'epoch': Epoch,
    'observation': Observation,
    'alert': Alert,
    'file_type': FileType,
    'file': File,
    'recommendation_tag': RecommendationTag,
    'recommendation': Recommendation,
    'model_type': ModelType,
    'model': Model,
    'level': Level,
    'topic': Topic,
    'host': Host,
    'message': Message,
    'subscriber': Subscriber,
    'access': Access,
}


# global registry of indices
indices: Dict[str, Index] = {
    'recommendation_object_index': recommendation_object_index,
    'recommendation_epoch_user_index': recommendation_epoch_user_index,
    'recommendation_user_facility_index': recommendation_user_facility_index,
    'observation_time_index': observation_time_index,
    'observation_object_index': observation_object_index,
    'observation_recorded_index': observation_recorded_index,
    'observation_source_object_index': observation_source_object_index,
}


# optionally defined depending on provider
if config.provider in ('timescale', ):
    indices['message_id_index'] = message_id_index
else:
    indices['message_time_topic_index'] = message_time_topic_index
