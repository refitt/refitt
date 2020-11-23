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

"""Core database ORM definitions for REFITT."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Type, Union, Optional

# standard libs
import logging
from datetime import datetime, timedelta

# external libs
from sqlalchemy import Column, ForeignKey, Index, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import Integer, BigInteger, DateTime, Float, Text, String, JSON, Boolean
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


class NotFound(NoResultFound):
    """Exception specific to no record found on lookup by unique field (e.g., `id`)."""


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
                data[name] = getattr(self, name).embedded()
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
        except IntegrityError:
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
        except IntegrityError:
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
    def delete(cls, id: int) -> None:
        """Cascade delete to Client and Session."""
        session = _Session()
        for client in session.query(Client).filter(Client.user_id == id):
            for _session in session.query(Session).filter(Session.client_id == client.id):
                session.delete(_session)
                session.commit()
                log.info(f'Deleted session for user ({id})')
            session.delete(client)
            session.commit()
            log.info(f'Deleted client for user ({id})')
        session.delete(cls.from_id(id, session))
        session.commit()
        log.info(f'Deleted user ({id})')


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
    def new_secret(cls, user_id: int) -> Secret:
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
        return secret

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
DEFAULT_EXPIRE_TIME = 900  # 15 minutes


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


# global registry of tables
tables: Dict[str, Base] = {

    'facility': Facility,
    'user': User,
    'facility_map': FacilityMap,

    'client': Client,
    'session': Session,

    'level': Level,
    'topic': Topic,
    'host': Host,
    'message': Message,
    'subscriber': Subscriber,
    'access': Access,
}
