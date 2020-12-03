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
from typing import List, Tuple, Dict, Any, Type, Optional

# standard libs
import logging
from datetime import datetime, timedelta

# external libs
from sqlalchemy import Column, ForeignKey, Index, func, type_coerce
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
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

    def embedded(self, join: bool = True) -> Dict[str, Any]:
        """Similar to :meth:`to_dict` but with `join` and serializable values."""
        data = {}
        for name, dtype in self.columns.items():
            value = getattr(self, name)
            if dtype is datetime:
                data[name] = str(value)
            else:
                data[name] = value
        if join:
            for name in self.relationships:
                child = getattr(self, name)
                if child:
                    data[name] = child.embedded(join=join)
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
            raise NotFound(f'No {cls.__name__.lower()} with id={id}') from error

    @classmethod
    def add(cls, data: dict) -> Optional[int]:
        """Add record from existing `data`, return `id` if applicable."""
        session = _Session()
        try:
            record = cls.from_dict(data)
            session.add(record)
            session.commit()
            log.info(f'Added {cls.__name__.lower()} ({record.id})')
            return record.id
        except (IntegrityError, DatabaseError):
            session.rollback()
            raise

    @classmethod
    def update(cls, id: int, **data) -> None:
        """Update named attributes of specified record."""
        session = _Session()
        try:
            record = cls.from_id(id, session)
            for field, value in data.items():
                if field in cls.columns:
                    setattr(record, field, value)
                else:
                    record.data = {**record.data, field: value}
            session.commit()
            log.info(f'Updated {cls.__name__.lower()} ({id})')
        except (IntegrityError, DatabaseError):
            session.rollback()
            raise

    @classmethod
    def delete(cls, id: int) -> None:
        """Delete existing record with `id`."""
        session = _Session()
        record = cls.from_id(id, session)
        session.delete(record)
        session.commit()
        log.info(f'Deleted {cls.__name__.lower()} ({id})')

    @classmethod
    def count(cls, session: _Session = None) -> int:
        """Count of records in table."""
        session = session or _Session()
        return session.query(cls).count()


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

    @classmethod
    def from_email(cls, address: str, session: _Session = None) -> User:
        """Query by unique email `address`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.email == address).one()
        except NoResultFound as error:
            raise NotFound(f'No user with email={address}') from error

    @classmethod
    def from_alias(cls, alias: str, session: _Session = None) -> User:
        """Query by unique `alias`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.alias == alias).one()
        except NoResultFound as error:
            raise NotFound(f'No user with alias={alias}') from error

    def facilities(self, session: _Session = None) -> List[Facility]:
        """Facilities associated with this user (queries `facility_map`)."""
        session = session or _Session()
        return session.query(Facility).join(FacilityMap).filter(FacilityMap.user_id == self.id).all()

    def add_facility(self, facility_id: int) -> None:
        """Associate `facility` with this user."""
        session = _Session()
        try:
            facility = Facility.from_id(facility_id, session)
        except NoResultFound as error:
            raise NotFound(f'No facility with id={facility_id}') from error
        session.add(FacilityMap(user_id=self.id, facility_id=facility.id))
        session.commit()
        log.info(f'Associated facility ({facility.id}) with user ({self.id})')

    def delete_facility(self, facility_id: int) -> None:
        """Dissociate facility with this user."""
        session = _Session()
        try:
            facility = Facility.from_id(facility_id, session)
        except NoResultFound as error:
            raise NotFound(f'No facility with id={facility_id}') from error
        for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == self.id,
                                                         FacilityMap.facility_id == facility.id):
            session.delete(mapping)
        session.commit()
        log.info(f'Dissociated facility ({facility.id}) from user ({self.id})')

    @classmethod
    def delete(cls, user_id: int) -> None:
        """Cascade delete to Client, Session, and FacilityMap."""
        session = _Session()
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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Facility:
        """Query by unique `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No facility with name={name}') from error

    def users(self, session: _Session = None) -> List[User]:
        """Users associated with this facility (queries `facility_map`)."""
        session = session or _Session()
        return session.query(User).join(FacilityMap).filter(FacilityMap.facility_id == self.id).all()

    def add_user(self, user_id: int) -> None:
        """Associate user with this facility."""
        session = _Session()
        try:
            user = User.from_id(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No user with id={user_id}') from error
        session.add(FacilityMap(user_id=user.id, facility_id=self.id))
        session.commit()
        log.info(f'Associated facility ({self.id}) with user ({user.id})')

    def delete_user(self, user_id: int) -> None:
        """Dissociate `user` with this facility."""
        session = _Session()
        try:
            user = User.from_id(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No user with id={user_id}') from error
        for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == user.id,
                                                         FacilityMap.facility_id == self.id):
            session.delete(mapping)
        session.commit()
        log.info(f'Dissociated facility ({self.id}) from user ({user.id})')

    @classmethod
    def delete(cls, facility_id: int) -> None:
        """Cascade delete to FacilityMap."""
        session = _Session()
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
    def add(cls, data: dict) -> Optional[int]:
        raise NotImplementedError()

    @classmethod
    def delete(cls, id: int) -> None:
        raise NotImplementedError()

    @classmethod
    def update(cls, id: int, **data) -> None:
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

    @classmethod
    def from_key(cls, key: str, session: _Session = None) -> Client:
        """Query by unique `key`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.key == key).one()
        except NoResultFound as error:
            raise NotFound(f'No client with key={key}') from error

    @classmethod
    def from_user(cls, user_id: int, session: _Session = None) -> Client:
        """Query by unique `user_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.user_id == user_id).one()
        except NoResultFound as error:
            raise NotFound(f'No client with user_id={user_id}') from error

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
        try:
            user = User.from_id(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No user with id={user_id}') from error
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
        try:
            client = Client.from_user(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No client with user_id={user_id}') from error
        secret = Secret.generate()
        client.secret = secret.hashed().value
        session.commit()
        log.info(f'Updated client secret for user ({client.user_id})')
        return Key(client.key), secret

    @classmethod
    def new_key(cls, user_id: int) -> Tuple[Key, Secret]:
        """Generate a new key and secret (store the hashed value)."""
        session = _Session()
        try:
            client = Client.from_user(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No client with user_id={user_id}') from error
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
    expires = Column('expires', DateTime(timezone=True), nullable=False)
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

    @classmethod
    def from_client(cls, client_id: int, session: _Session = None) -> Session:
        """Query by unique client `id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.client_id == client_id).one()
        except NoResultFound as error:
            raise NotFound(f'No session with client_id={client_id}') from error

    @classmethod
    def new(cls, user_id: int) -> JWT:
        """Create new session for `user`."""
        session = _Session()
        try:
            client = Client.from_user(user_id, session)
        except NoResultFound as error:
            raise NotFound(f'No client with user_id={user_id}') from error
        jwt = JWT(sub=client.id, exp=timedelta(seconds=DEFAULT_EXPIRE_TIME))
        token = Token(jwt.encrypt()).hashed().value
        try:
            old = Session.from_client(client.id, session)
            old.expires = jwt.exp
            old.token = token
            old.created = datetime.now()
        except NoResultFound:
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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ObjectType:
        """Query by unique object_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No object_type with name={name}') from error


class Object(Base, CoreMixin):
    """Object table."""

    __tablename__ = 'object'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer(), primary_key=True, nullable=False)
    type_id = Column('type_id', Integer(), ForeignKey(ObjectType.id), nullable=False)
    name = Column('name', Text(), unique=True, nullable=False)
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
        'name': str,
        'aliases': dict,
        'ra': float,
        'dec': float,
        'redshift': float,
        'data': dict,
    }

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Object:
        """Query by unique object `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No object with name={name}') from error

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
            raise NotFound(f'No object with alias {provider}={name}') from error
        except MultipleResultsFound as error:
            raise NotDistinct(f'Multiple objects with alias {provider}={name}') from error

    @classmethod
    def add_alias(cls, object_id: int, **aliases: str) -> None:
        """Add alias(es) to the given object."""
        session = _Session()
        try:
            obj = Object.from_id(object_id, session)
            for provider, name in aliases.items():
                try:
                    existing = Object.from_alias(session, **{provider: name, })
                    if existing.id != object_id:
                        raise AlreadyExists(f'Object with alias {provider}={name} already exists')
                except NotFound:
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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ObservationType:
        """Query by unique observation_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No observation_type with name={name}') from error


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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> SourceType:
        """Query by unique source_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No source_type with name={name}') from error


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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Source:
        """Query by unique source `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No source with name={name}') from error

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

    @classmethod
    def with_object(cls, object_id: int, session: _Session = None) -> List[Observation]:
        """All observations with `object_id`."""
        session = session or _Session()
        return session.query(cls).filter(cls.object_id == object_id).all()

    @classmethod
    def with_source(cls, source_id: int, session: _Session = None) -> List[Observation]:
        """All observations with `source_id`."""
        session = session or _Session()
        return session.query(cls).filter(cls.source_id == source_id).all()


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

    @classmethod
    def from_observation(cls, observation_id: int, session: _Session = None) -> Alert:
        """Query by unique alert `observation_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.observation_id == observation_id).one()
        except NoResultFound as error:
            raise NotFound(f'No alert with observation_id={observation_id}') from error


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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> FileType:
        """Query by unique file_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No file_type with name={name}') from error


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

    @classmethod
    def from_observation(cls, observation_id: str, session: _Session = None) -> File:
        """Query by unique file `observation_id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.observation_id == observation_id).one()
        except NoResultFound as error:
            raise NotFound(f'No file with observation_id={observation_id}') from error


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

    @classmethod
    def from_id(cls, id: int, session: _Session = None) -> RecommendationGroup:
        """Query by unique `id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.id == id).one()
        except NoResultFound as error:
            raise NotFound(f'No recommendation_group with id={id}') from error

    @classmethod
    def new(cls, session: _Session = None) -> RecommendationGroup:
        """Create and return a new recommendation group."""
        session = session or _Session()
        group = cls()
        session.add(group)
        session.commit()
        return group

    @classmethod
    def latest(cls, session: _Session = None) -> RecommendationGroup:
        """Get the most recent recommendation group."""
        session = session or _Session()
        return session.query(cls).order_by(cls.created.desc()).first()

    @classmethod
    def select(cls, limit: int, offset: int = None, session: _Session = None) -> List[RecommendationGroup]:
        """Select a range of recommendation groups."""
        session = session or _Session()
        query = session.query(cls).order_by(cls.id.desc())
        if offset:
            return query[offset:offset+limit]
        else:
            return query.limit(limit)


class Recommendation(Base, CoreMixin):
    """Recommendation table."""

    __tablename__ = 'recommendation'
    __table_args__ = {'schema': schema}

    id = Column('id', Integer().with_variant(BigInteger(), 'postgresql'), primary_key=True, nullable=False)
    group_id = Column('group_id', Integer(), ForeignKey(RecommendationGroup.id), nullable=False)
    time = Column('time', DateTime(timezone=True), nullable=False, server_default=func.now())
    priority = Column('priority', Integer(), nullable=False)
    facility_id = Column('facility_id', Integer(), ForeignKey(Facility.id), nullable=False)
    user_id = Column('user_id', Integer(), ForeignKey(User.id), nullable=False)
    object_id = Column('object_id', Integer(), ForeignKey(Object.id), nullable=False)
    predicted_observation_id = Column('predicted_observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                                      ForeignKey(Observation.id), nullable=True)
    observation_id = Column('observation_id', Integer().with_variant(BigInteger(), 'postgresql'),
                            ForeignKey(Observation.id), nullable=True)
    accepted = Column('accepted', Boolean(), nullable=False, default=False)
    rejected = Column('rejected', Boolean(), nullable=False, default=False)
    data = Column('data', JSON().with_variant(JSONB(), 'postgresql'), nullable=False, default={})

    group = relationship(RecommendationGroup, backref='recommendation')
    user = relationship(User, backref='recommendation')
    facility = relationship(Facility, backref='recommendation')
    object = relationship(Object, backref='recommendation')
    predicted = relationship(Observation, foreign_keys=[predicted_observation_id, ])
    observed = relationship(Observation, foreign_keys=[observation_id, ])

    relationships = {'user': User, 'facility': Facility, 'predicted': Observation, 'observed': Observation}
    columns = {
        'id': int,
        'group_id': int,
        'time': datetime,
        'priority': int,
        'facility_id': int,
        'user_id': int,
        'object_id': int,
        'predicted_observation_id': int,
        'observation_id': int,
        'accepted': bool,
        'rejected': bool,
        'data': dict
    }

    @classmethod
    def from_id(cls, id: int, session: _Session = None) -> Recommendation:
        """Query by unique `id`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.id == id).one()
        except NoResultFound as error:
            raise NotFound(f'No recommendation with id={id}') from error

    @classmethod
    def for_user(cls, user_id: int, group_id: int = None, session: _Session = None) -> List[Recommendation]:
        """Select recommendations for the given user and group."""
        session = session or _Session()
        group_id = group_id or RecommendationGroup.latest(session).id
        return (session.query(cls).order_by(cls.priority)
                .filter(cls.group_id == group_id).filter(cls.user_id == user_id)).all()

    @classmethod
    def next(cls, user_id: int, group_id: int = None, limit: int = None) -> None:
        """
        Select next recommendation for the given user and group, with the highest priority
        that has neither been 'accepted' nor 'rejected', up to some limit.
        """
        session = _Session()
        query = session.query(cls).order_by(cls.priority)
        query = query.filter(cls.user_id == user_id)
        query = query.filter(cls.group_id == (group_id or RecommendationGroup.latest(session).id))
        query = query.filter(cls.accepted == False).filter(cls.rejected == False)
        if limit:
            return query.limit(limit)
        else:
            return query.all()


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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> ModelType:
        """Query by unique model_type `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No model_type with name={name}') from error


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

    @classmethod
    def from_name(cls, name: str, session: _Session = None) -> Model:
        """Query by unique model `name`."""
        try:
            session = session or _Session()
            return session.query(cls).filter(cls.name == name).one()
        except NoResultFound as error:
            raise NotFound(f'No model with name={name}') from error


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
    'alert': Alert,
    'file_type': FileType,
    'file': File,
    'recommendation_group': RecommendationGroup,
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
