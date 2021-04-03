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

"""Core database ORM definitions."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Type, Optional, Callable, TypeVar, Union

# standard libs
import random
import logging
from base64 import encodebytes as base64_encode, decodebytes as base64_decode
from datetime import datetime, timedelta
from functools import lru_cache

# external libs
from names_generator.names import LEFT, RIGHT
from sqlalchemy import Column, ForeignKey, Index, func, type_coerce, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, aliased, Query
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.types import Integer, BigInteger, DateTime, Float, Text, String, JSON, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB

# internal libs
from .core import schema, Session as _Session
from ..web.token import Key, Secret, Token, JWT

# NOTE: declarative base is imported from StreamKit's ORM.
# This does not relate to the engine/session itself and we don't do anything with them.
# It helps to have them share a base with our tables for initialization.
from streamkit.database.core.orm import Table as Base
from streamkit.database.core.orm import Level, Topic, Host, Message, Subscriber, Access


# initialize module level logger
log = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Generic error with respect to the database model."""


class NotFound(NoResultFound):
    """Exception specific to no record found on lookup by unique field (e.g., `id`)."""


class NotDistinct(MultipleResultsFound):
    """Exception specific to multiple records found when only one should have been."""


class AlreadyExists(DatabaseError):
    """Exception specific to a record with unique properties already existing."""


# JSON value types and their coerced type before loading into database
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


# list of defined type coercion filters
__LM = Callable[[__VT], __RT]
__DM = Callable[[__RT], __VT]
__loaders: List[__LM] = [__load_datetime, __load_bytes, ]
__dumpers: List[__DM] = [__dump_datetime, __dump_bytes, ]


def __load_imp(value: __VT, filters: List[__LM]) -> __RT:
    return value if not filters else filters[0](__load_imp(value, filters[1:]))


def _load(value: __VT) -> __RT:
    """Passively coerce value types of stored record assets to database compatible types."""
    return __load_imp(value, __loaders)


def __dump_imp(value: __RT, filters: List[__DM]) -> __VT:
    return value if not filters else filters[0](__dump_imp(value, filters[1:]))


def _dump(value: __RT) -> __VT:
    """Passively coerce database types to JSON encoded types."""
    return __dump_imp(value, __dumpers)


class CoreMixin:
    """Core mixin class for all models."""

    columns: Dict[str, type] = {}
    relationships: Dict[str, Type[Base]] = {}

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
    def from_dict(cls: Type[Base], data: Dict[str, Any]) -> Base:
        """Build record from existing dictionary."""
        return cls(**data)

    @classmethod
    def from_json(cls: Type[Base], data: Dict[str, __VT]) -> Base:
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
                record = getattr(self, name)
                if record is not None:
                    data[name] = record.to_json(join=True)
        return data

    @classmethod
    def from_id(cls: Type[Base], id: int, session: _Session = None) -> Base:
        """Query for record using unique `id` if applicable."""
        try:
            if hasattr(cls, 'id'):
                session = session or _Session()
                return session.query(cls).filter(cls.id == id).one()
            else:
                raise AttributeError(f'{cls} has no `id` attribute')
        except NoResultFound as error:
            raise cls.NotFound(f'No {cls.__tablename__} with id={id}') from error

    @classmethod
    def add(cls: Type[Base], data: dict, session: _Session = None) -> Base:
        """Add record from existing `data`, return constructed record."""
        record, = cls.add_all([data, ], session=session)
        return record

    @classmethod
    def add_all(cls: Type[Base], data: List[dict], session: _Session = None) -> List[Base]:
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
    def update(cls: Type[Base], id: int, session: Session = None, **data) -> Base:
        """Update named attributes of specified record."""
        session = session or _Session()
        try:
            record = cls.from_id(id, session)
            for field, value in data.items():
                if field in cls.columns:
                    setattr(record, field, value)
                else:
                    record.data = {**record.data, field: value}
            session.commit()
            log.info(f'Updated {cls.__tablename__} ({id})')
            return record
        except (IntegrityError, DatabaseError):
            session.rollback()
            raise

    @classmethod
    def delete(cls: Type[Base], id: int, session: _Session = None) -> None:
        """Delete existing record with `id`."""
        session = session or _Session()
        record = cls.from_id(id, session)
        session.delete(record)
        session.commit()
        log.info(f'Deleted {cls.__tablename__} ({id})')

    @classmethod
    def count(cls, session: _Session = None) -> int:
        """Count of records in table."""
        session = session or _Session()
        return session.query(cls).count()

    @classmethod
    def query(cls: Type[Base]) -> Query:
        return _Session.query(cls)


# NOTE: patch existing table definitions.
# This is a hack and will be redone at a later point (likely improvement to StreamKit).
Level.from_json = lambda data: Level(**{k: _load(v) for k, v in data.items()})
Topic.from_json = lambda data: Topic(**{k: _load(v) for k, v in data.items()})
Host.from_json = lambda data: Host(**{k: _load(v) for k, v in data.items()})
Message.from_json = lambda data: Message(**{k: _load(v) for k, v in data.items()})
Subscriber.from_json = lambda data: Subscriber(**{k: _load(v) for k, v in data.items()})
Access.from_json = lambda data: Access(**{k: _load(v) for k, v in data.items()})
Level.to_tuple = Level.values
Topic.to_tuple = Topic.values
Host.to_tuple = Host.values
Message.to_tuple = Message.values
Subscriber.to_tuple = Subscriber.values
Access.to_tuple = Access.values
Level.columns = {'id': int, 'name': str}
Level.relationships = {}
Topic.columns = {'id': int, 'name': str}
Topic.relationships = {}
Host.columns = {'id': int, 'name': str}
Host.relationships = {}
Subscriber.columns = {'id': int, 'name': str}
Subscriber.relationships = {}
Access.columns = {'subscriber_id': int, 'topic_id': int, 'time': datetime}
Access.relationships = {'subscriber': Subscriber, 'topic': Topic}
Message.columns = {'id': int, 'time': datetime, 'topic_id': int, 'level_id': int, 'host_id': int, 'text': str}
Message.relationships = {'topic': Topic, 'level': Level, 'host': Host}


class User(Base, CoreMixin):
    """User profiles store characteristics about a person."""

    __tablename__ = 'user'
    __table_args__ = {'schema': schema}

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


class Facility(Base, CoreMixin):
    """Facility profiles store characteristics about a telescope and it's instruments."""

    __tablename__ = 'facility'
    __table_args__ = {'schema': schema}

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


class FacilityMap(Base, CoreMixin):
    """Mapping table between users and facilities."""

    __tablename__ = 'facility_map'
    __table_args__ = {'schema': schema}

    user_id = Column('user_id', Integer(), ForeignKey(User.id, ondelete='cascade'),
                     primary_key=True, nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id, ondelete='cascade'),
                         primary_key=True, nullable=False)

    columns = {
        'user_id': int,
        'facility_id': int
    }

    @classmethod
    def from_id(cls: Type[Base], id: int, session: _Session = None) -> Base:
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


# New credentials will be initialized with this level unless
# otherwise specified
DEFAULT_CLIENT_LEVEL: int = 10


class Client(Base, CoreMixin):
    """Client stores user authorization and authentication."""

    __tablename__ = 'client'
    __table_args__ = {'schema': schema}

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
        """
        Create client credentials for `user` with `level`.

        Args:
            user_id (int or `User`):
                An existing user.

            level (int):
                Authorization level (default: `DEFAULT_CLIENT_LEVEL`).
        """
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


# New session tokens if not otherwise requested will have
# the following lifetime (seconds)
DEFAULT_EXPIRE_TIME: int = 900  # 15 minutes


class Session(Base, CoreMixin):
    """Session stores hashed token with claim details."""

    __tablename__ = 'session'
    __table_args__ = {'schema': schema}

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


class ObjectType(Base, CoreMixin):
    """Object types (e.g., 'SNIa')."""

    __tablename__ = 'object_type'
    __table_args__ = {'schema': schema}

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


class Object(Base, CoreMixin):
    """Object table."""

    __tablename__ = 'object'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer(), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ObjectType.id), nullable=False)
    aliases = Column('aliases', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})
    ra = Column('ra', Float(), nullable=False)
    dec = Column('dec', Float(), nullable=False)
    redshift = Column('redshift', Float(), nullable=True)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    type = relationship(ObjectType, backref='object')

    relationships = {'type': ObjectType}
    columns = {
        'id': int,
        'type_id': int,
        'aliases': dict,
        'ra': float,
        'dec': float,
        'redshift': float,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to ObjectType."""

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
                    obj.aliases[provider] = name
            session.commit()
        except (IntegrityError, AlreadyExists):
            session.rollback()
            raise


class ObservationType(Base, CoreMixin):
    """Observation types (e.g., 'g-ztf')."""

    __tablename__ = 'observation_type'
    __table_args__ = {'schema': schema}

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


class SourceType(Base, CoreMixin):
    """Source types (e.g., 'broker')."""

    __tablename__ = 'source_type'
    __table_args__ = {'schema': schema}

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


class Source(Base, CoreMixin):
    """Source table."""

    __tablename__ = 'source'
    __table_args__ = {'schema': schema}

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


class Observation(Base, CoreMixin):
    """Observation table."""

    __tablename__ = 'observation'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ObservationType.id), nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), nullable=False)
    source_id = Column('source_id', Integer(), ForeignKey(Source.id), nullable=False)
    value = Column('value', Float(), nullable=False)
    error = Column('error', Float(), nullable=True)
    time = Column('time', DateTime(timezone=True), nullable=False)
    recorded = Column('recorded', DateTime(timezone=True), nullable=False, server_default=func.now())

    type = relationship(ObservationType, backref='observation')
    object = relationship(Object, backref='observation')
    source = relationship(Source, backref='observation')

    relationships = {'type': ObservationType, 'object': Object, 'source': Source}
    columns = {
        'id': int,
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


# indices for observation table
observation_object_index = Index('observation_object_index', Observation.object_id)
observation_source_object_index = Index('observation_source_object_index', Observation.source_id, Observation.object_id)
observation_time_index = Index('observation_time_index', Observation.time)
observation_recorded_index = Index('observation_recorded_index', Observation.recorded)


class Alert(Base, CoreMixin):
    """Alert table."""

    __tablename__ = 'alert'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), unique=True, nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False)

    observation = relationship(Observation, backref='alert')

    relationships = {'observation': Observation}
    columns = {
        'id': int,
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


class FileType(Base, CoreMixin):
    """File type table."""

    __tablename__ = 'file_type'
    __table_args__ = {'schema': schema}

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


class File(Base, CoreMixin):
    """File table."""

    __tablename__ = 'file'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), unique=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(FileType.id), nullable=False)
    data = Column('data', LargeBinary(), nullable=False)

    type = relationship(FileType, backref='file')
    observation = relationship(Observation, backref='file')

    relationships = {'type': FileType, 'observation': Observation}
    columns = {
        'id': int,
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


class Forecast(Base, CoreMixin):
    """Forecast table."""

    __tablename__ = 'forecast'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), unique=True, nullable=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False)

    observation = relationship(Observation, backref='forecast')

    relationships = {'observation': Observation}
    columns = {
        'id': int,
        'observation_id': int,
        'data': dict,
    }

    class NotFound(NotFound):
        """NotFound exception specific to Forecast."""

    @classmethod
    def from_observation(cls, observation_id: int, session: _Session = None) -> Alert:
        """Query by unique forecast `observation_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.observation_id == observation_id).one()
        except NoResultFound as error:
            raise Forecast.NotFound(f'No forecast with observation_id={observation_id}') from error


class RecommendationGroup(Base, CoreMixin):
    """Recommendation group table."""

    __tablename__ = 'recommendation_group'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer(), primary_key=True, nullable=False)
    created = Column('created', DateTime(timezone=True), nullable=False, server_default=func.now())

    columns = {
        'id': int,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to RecommendationGroup."""

    @classmethod
    def new(cls, session: _Session = None) -> RecommendationGroup:
        """Create and return a new recommendation group."""
        return cls.add({}, session=session)

    @classmethod
    def latest(cls, session: _Session = None) -> RecommendationGroup:
        """Get the most recent recommendation group."""
        session = session or _Session()
        return session.query(cls).order_by(cls.id.desc()).first()

    @classmethod
    def select(cls, limit: int, offset: int = 0) -> List[RecommendationGroup]:
        """Select a range of recommendation groups."""
        return cls.query().order_by(cls.id.desc()).filter(cls.id <= cls.latest().id - offset).limit(limit).all()


class RecommendationTag(Base, CoreMixin):
    """Recommendation tag table."""

    __tablename__ = 'recommendation_tag'
    __table_args__ = {'schema': schema}

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


class Recommendation(Base, CoreMixin):
    """Recommendation table."""

    __tablename__ = 'recommendation'
    __table_args__ = {'schema': schema}

    id = Column('id', BigInteger().with_variant(Integer(), 'sqlite'), primary_key=True, nullable=False)
    group_id = Column('group_id', Integer(), ForeignKey(RecommendationGroup.id), nullable=False)
    tag_id = Column('tag_id', Integer(), ForeignKey(RecommendationTag.id), nullable=False)
    time = Column('time', DateTime(timezone=True), nullable=False, server_default=func.now())
    priority = Column('priority', Integer(), nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id), nullable=False)
    user_id = Column('user_id', Integer(), ForeignKey(User.id), nullable=False)
    forecast_id = Column('forecast_id', BigInteger().with_variant(Integer(), 'sqlite'),
                         ForeignKey(Forecast.id), nullable=True)
    predicted_observation_id = Column('predicted_observation_id', BigInteger().with_variant(Integer(), 'sqlite'),
                                      ForeignKey(Observation.id), nullable=True)
    observation_id = Column('observation_id', BigInteger().with_variant(Integer(), 'sqlite'),
                            ForeignKey(Observation.id), nullable=True)
    accepted = Column('accepted', Boolean(), nullable=False, default=False)
    rejected = Column('rejected', Boolean(), nullable=False, default=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    group = relationship(RecommendationGroup, backref='recommendation')
    tag = relationship(RecommendationTag, backref='recommendation')
    user = relationship(User, backref='recommendation')
    facility = relationship(Facility, backref='recommendation')
    object = relationship(Object, backref='recommendation')
    forecast = relationship(Forecast, backref='recommendation')
    predicted = relationship(Observation, foreign_keys=[predicted_observation_id, ])
    observed = relationship(Observation, foreign_keys=[observation_id, ])

    relationships = {'group': RecommendationGroup, 'tag': RecommendationTag, 'user': User, 
                     'facility': Facility, 'object': Object, 'forecast': Forecast, 
                     'predicted': Observation, 'observed': Observation}
    columns = {
        'id': int,
        'group_id': int,
        'tag_id': int,
        'time': datetime,
        'priority': int,
        'object_id': int,
        'facility_id': int,
        'user_id': int,
        'forecast_id': int,
        'predicted_observation_id': int,
        'observation_id': int,
        'accepted': bool,
        'rejected': bool,
        'data': dict
    }

    class NotFound(NotFound):
        """NotFound exception specific to Recommendation."""

    @classmethod
    def for_user(cls, user_id: int, group_id: int = None, session: _Session = None) -> List[Recommendation]:
        """Select recommendations for the given user and group."""
        session = session or _Session()
        group_id = group_id or RecommendationGroup.latest(session).id
        return (session.query(cls).order_by(cls.priority)
                .filter(cls.group_id == group_id, cls.user_id == user_id)).all()

    @classmethod
    def next(cls, user_id: int, group_id: int = None, limit: int = None,
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
        query = query.filter(cls.group_id == (group_id or RecommendationGroup.latest(session).id))
        query = query.filter(cls.accepted == False).filter(cls.rejected == False)
        if facility_id is not None:
            query = query.filter(cls.facility_id == facility_id)
        if limiting_magnitude is not None:
            query = query.filter(predicted.value <= limiting_magnitude)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def history(cls, user_id: int, group_id: int) -> List[Recommendation]:
        """
        Select previous recommendations that the user has either affirmatively
        accepted OR rejected.
        """
        return (cls.query().order_by(cls.id)
                .filter(cls.user_id == user_id).filter(cls.group_id == group_id)
                .filter(or_(cls.accepted == True, cls.rejected == True))).all()


# indices for recommendation table
recommendation_object_index = Index('recommendation_object_index', Recommendation.object_id)
recommendation_user_facility_index = Index('recommendation_user_facility_index',
                                           Recommendation.user_id, Recommendation.facility_id)
recommendation_group_user_index = Index('recommendation_group_user_index',
                                        Recommendation.group_id, Recommendation.user_id)


class ModelType(Base, CoreMixin):
    """Model type table."""

    __tablename__ = 'model_type'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer(), primary_key=True, nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    format = Column('format', Text(), nullable=False)
    description = Column('description', Text(), nullable=False)

    columns = {
        'id': int,
        'name': str,
        'format': str,
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


class Model(Base, CoreMixin):
    """Model table."""

    __tablename__ = 'model'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ModelType.id), nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
    hash = Column('hash', String(64), nullable=False)
    accuracy = Column('accuracy', Float(), nullable=True)
    data = Column('data', LargeBinary(), nullable=False)
    created = Column('created', DateTime(timezone=True), nullable=False, server_default=func.now())

    type = relationship(ModelType, backref='model')

    relationships = {'type': ModelType}
    columns = {
        'id': int,
        'type_id': int,
        'name': str,
        'hash': str,
        'accuracy': float,
        'data': bytes,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Model."""

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Model:
        """Query by unique model `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise Model.NotFound(f'No model with name={name}') from error


# global registry of tables
tables: Dict[str, Base] = {
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
    'observation': Observation,
    'forecast': Forecast,
    'alert': Alert,
    'file_type': FileType,
    'file': File,
    'recommendation_group': RecommendationGroup,
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
    'recommendation_group_user_index': recommendation_group_user_index,
    'recommendation_user_facility_index': recommendation_user_facility_index,
    'observation_time_index': observation_time_index,
    'observation_object_index': observation_object_index,
    'observation_recorded_index': observation_recorded_index,
    'observation_source_object_index': observation_source_object_index,
}
