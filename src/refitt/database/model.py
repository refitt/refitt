# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database entities and operations."""


# type annotations
from __future__ import annotations
from typing import List, Tuple, Dict, Any, Type, Optional, Union, Protocol, Final

# standard libs
import re
import json
import random
from datetime import datetime, timedelta
from functools import lru_cache
from dataclasses import dataclass

# external libs
from pandas import DataFrame, DatetimeIndex
from names_generator.names import LEFT, RIGHT
from sqlalchemy import ForeignKey, Index, func, or_
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship, aliased, Query, scoped_session
from sqlalchemy.exc import IntegrityError, NoResultFound, MultipleResultsFound
from sqlalchemy.dialects.postgresql import JSON as SQLJSONB
from sqlalchemy.types import (Integer as SQLInteger,
                              BigInteger as SQLBigInteger,
                              DateTime as SQLDateTime,
                              Float as SQLFloat,
                              Text as SQLText,
                              String as SQLString,
                              JSON as SQLJSON,
                              Boolean as SQLBoolean,
                              LargeBinary as SQLLargeBinary)

# internal libs
from refitt.core.config import config
from refitt.core.logging import Logger
from refitt.database.core import NotFound, NotDistinct, AlreadyExists, _load, _dump
from refitt.database.connection import default_connection as db
from refitt.web.token import Key, Secret, Token, JWT

# public interface
__all__ = ['IntegrityError',
           'Entity', 'Level', 'Topic', 'Host', 'Subscriber', 'Message', 'Access',
           'User', 'Facility', 'FacilityMap', 'ObjectType', 'Object', 'SourceType',
           'Source', 'ObservationType', 'Observation', 'Alert', 'FileType', 'File',
           'RecommendationTag', 'Epoch', 'Recommendation', 'ModelType', 'Model',
           'Client', 'Session', 'tables', 'indices', 'DEFAULT_EXPIRE_TIME', 'DEFAULT_CLIENT_LEVEL', ]

# module logger
log = Logger.with_name(__name__)


class EntityMixin:
    """Core mixin class for all entities."""

    @declared_attr
    def __tablename__(cls: Type[Entity]) -> str:  # noqa: cls
        """The table name should be the "snake_case" of the "ClassName"."""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()

    @declared_attr
    def __table_args__(cls: Type[Entity]) -> Dict[str, Any]:  # noqa: cls
        """Common table attributes."""
        return {'schema': config.database.get('schema', config.database.default.get('schema')), }

    columns: Dict[str, type] = {}
    relationships: Dict[str, Type[Entity]] = {}

    def __repr__(self: Entity) -> str:
        """String representation of record."""
        attrs = ', '.join([f'{name}={repr(getattr(self, name))}' for name in self.columns])
        return f'<{self.__class__.__name__}({attrs})>'

    def to_tuple(self: Entity) -> tuple:
        """Convert fields into standard tuple."""
        return tuple([getattr(self, name) for name in self.columns])

    def to_dict(self: Entity) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return {name: getattr(self, name) for name in self.columns}

    @classmethod
    def from_dict(cls: Type[Entity], data: Dict[str, Any]) -> Entity:
        """Build record from existing dictionary."""
        return cls(**data)

    @classmethod
    def new(cls: Type[Entity], **fields) -> Entity:
        """Create new instance of the model with default fields."""
        return cls(**fields)

    @classmethod
    def from_json(cls: Type[Entity], data: Dict[str, Any]) -> Entity:
        """Build record from JSON data (already loaded as dictionary)."""
        return cls.from_dict({k: _load(v) for k, v in data.items()})

    def to_json(self: Entity, pop: List[str] = None, join: bool = False) -> Dict[str, Any]:
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
                elif isinstance(relation, Entity):
                    data[name] = relation.to_json(join=True)
                elif relation is None:
                    pass
                else:
                    raise AttributeError(f'Unexpected {relation.__class__.__name__}({relation}) for '
                                         f'{self.__class__.__name__}.{name}')
        return data

    @classmethod
    def from_id(cls: Type[Entity], id: int, session: scoped_session = None) -> Entity:
        """Query with unique `id`."""
        try:
            return (session or db.read).query(cls).filter(cls.id == id).one()
        except NoResultFound as error:
            raise cls.NotFound(f'No {cls.__tablename__} with id={id}') from error

    @classmethod
    def add(cls: Type[Entity], data: dict, session: scoped_session = None) -> Entity:
        """Add record from existing `data`, return constructed record."""
        record, = cls.add_all([data, ], session)
        return record

    @classmethod
    def add_all(cls: Type[Entity],
                data: List[dict],
                session: scoped_session = None) -> List[Entity]:
        """Add list of new records to the database and return constructed records."""
        records = [cls.from_dict(record) for record in data]
        session = session or db.write
        try:
            session.add_all(records)
            session.commit()
            for record in records:
                log.debug(f'Added {cls.__tablename__} ({record.id})')
            return records
        except Exception:
            session.rollback()
            raise

    @classmethod
    def update(cls: Type[Entity], id: int, session: scoped_session = None, **data) -> Entity:
        """Update named attributes of specified record."""
        session = session or db.write
        record = cls.from_id(id, session)
        try:
            for field, value in data.items():
                if field in cls.columns:
                    setattr(record, field, value)
                    log.info(f'Updated {cls.__tablename__} ({id}: {field}={value})')
                else:
                    record.data = {**record.data, field: value}
                    log.info(f'Updated {cls.__tablename__} ({id}: data[{field}]={value})')
            session.commit()
            return record
        except Exception:
            session.rollback()
            raise

    @classmethod
    def delete(cls: Type[Entity], id: int, session: scoped_session = None) -> None:
        """Delete existing record with `id`."""
        session = session or db.write
        try:
            session.delete(cls.from_id(id, session))
            session.commit()
            log.info(f'Deleted {cls.__tablename__} ({id})')
        except Exception:
            session.rollback()
            raise

    @classmethod
    def count(cls: Type[Entity], session: scoped_session = None) -> int:
        """Count of records in the table."""
        return (session or db.read).query(cls).count()

    @classmethod
    def query(cls: Type[Entity], session: scoped_session = None) -> Query:
        """Basic query assumes read-only database session."""
        return (session or db.read).query(cls)

    @classmethod
    def load_first(cls: Type[Entity]) -> Entity:
        """Assumes read-only query on given entity class, returns first row."""
        return cls.query().first()

    @classmethod
    def load_all(cls: Type[Entity]) -> List[Entity]:
        """Assumes read-only query on given entity class, returns all rows."""
        return cls.query().all()


# declarative base inherits common interface
Entity = declarative_base(cls=EntityMixin)

# SQL types
INTEGER = SQLInteger()
BIG_INTEGER = SQLInteger().with_variant(SQLBigInteger(), 'postgresql')
FLOAT = SQLFloat()
TEXT = SQLText()
JSON = SQLJSON().with_variant(SQLJSONB(), 'postgresql')
STRING_16 = SQLString(16)
STRING_64 = SQLString(64)
BOOLEAN = SQLBoolean()
DATETIME = SQLDateTime(timezone=True)
BINARY = SQLLargeBinary()


class User(Entity):
    """User stores attributes about a participating human observer."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    first_name: Mapped[str] = mapped_column('first_name', TEXT, nullable=False)
    last_name: Mapped[str] = mapped_column('last_name', TEXT, nullable=False)
    email: Mapped[str] = mapped_column('email', TEXT, unique=True, nullable=False)
    alias: Mapped[str] = mapped_column('alias', TEXT, unique=True, nullable=False)
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False, default={})

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
    def from_email(cls: Type[User], address: str, session: scoped_session = None) -> User:
        """Query user by unique email `address`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(User).filter_by(email=address).one()  # noqa
        except NoResultFound as error:
            raise User.NotFound(f'No user with email={address}') from error

    @classmethod
    def from_alias(cls: Type[User], alias: str, session: scoped_session = None) -> User:
        """Query user by unique `alias`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter_by(alias=alias).one()  # noqa
        except NoResultFound as error:
            raise User.NotFound(f'No user with alias={alias}') from error

    def get_facilities(self: User, session: scoped_session = None) -> List[Facility]:
        """Facilities associated with this user (queries `facility_map`)."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read).query(Facility)
            .join(FacilityMap)
            .filter(FacilityMap.user_id == self.id)
            .order_by(FacilityMap.facility_id).all()
        )

    def add_facility(self: User, facility_id: int, session: scoped_session = None) -> None:
        """Associate `facility_id` with this user."""
        session = session or db.write
        Facility.from_id(facility_id, session)  # checks for Facility.NotFound
        try:
            session.query(FacilityMap).filter(FacilityMap.user_id == self.id,
                                              FacilityMap.facility_id == facility_id).one()
        except NoResultFound:
            session.add(FacilityMap(user_id=self.id, facility_id=facility_id))
            session.commit()
            log.info(f'Associated facility ({facility_id}) with user ({self.id})')
        except Exception:
            session.rollback()
            raise

    def remove_facility(self: User, facility_id: int, session: scoped_session = None) -> None:
        """Dissociate facility with this user."""
        session = session or db.write
        try:
            Facility.from_id(facility_id, session)  # checks for Facility.NotFound
            for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == self.id,
                                                             FacilityMap.facility_id == facility_id):
                session.delete(mapping)
                session.commit()
            log.info(f'Dissociated facility ({facility_id}) from user ({self.id})')
        except Exception:
            session.rollback()
            raise

    @classmethod
    def delete(cls: Type[User], user_id: int, session: scoped_session = None) -> None:
        """Cascade delete to Client, Session, and FacilityMap."""
        # NOTE: session commits occur immediately in order to allow the cascade :(
        session = session or db.write
        try:
            user = cls.from_id(user_id, session)
            for client in session.query(Client).filter(Client.user_id == user_id):
                for client_session in session.query(Session).filter(Session.client_id == client.id):
                    session.delete(client_session)
                    session.commit()  # NOTE: commit allows delete client
                    log.info(f'Deleted session for user ({user_id})')
                session.delete(client)
                session.commit()  # NOTE: commit allows delete user
                log.info(f'Deleted client for user ({user_id})')
            for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == user_id):
                session.delete(mapping)
                session.commit()  # NOTE: commit allows delete user
                log.info(f'Dissociated facility ({mapping.facility_id}) from user ({user_id})')
            session.delete(user)
            session.commit()
            log.info(f'Deleted user ({user_id})')
        except Exception:
            session.rollback()
            raise


class Facility(Entity):
    """Facility stores characteristics about a telescope and its instruments."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    latitude: Mapped[float] = mapped_column('latitude', FLOAT, nullable=False)
    longitude: Mapped[float] = mapped_column('longitude', FLOAT, nullable=False)
    elevation: Mapped[float] = mapped_column('elevation', FLOAT, nullable=False)
    limiting_magnitude: Mapped[float] = mapped_column('limiting_magnitude', FLOAT, nullable=False)
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False, default={})

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
    def from_name(cls: Type[Facility], name: str, session: scoped_session = None) -> Facility:
        """Query facility by unique `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(Facility).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Facility.NotFound(f'No facility with name={name}') from error

    def get_users(self: Facility, session: scoped_session = None) -> List[User]:
        """Query users associated with this facility (queries `facility_map`)."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read).query(User)
            .join(FacilityMap)
            .filter(FacilityMap.facility_id == self.id)
            .order_by(FacilityMap.user_id).all()
        )

    def add_user(self: Facility, user_id: int, session: scoped_session = None) -> None:
        """Associate user with this facility."""
        session = session or db.write
        try:
            User.from_id(user_id, session)  # checks for User.NotFound
            try:
                session.query(FacilityMap).filter(FacilityMap.user_id == user_id,
                                                  FacilityMap.facility_id == self.id).one()
            except NoResultFound:
                session.add(FacilityMap(user_id=user_id, facility_id=self.id))
                session.commit()
            log.info(f'Associated facility ({self.id}) with user ({user_id})')
        except Exception:
            session.rollback()
            raise

    def remove_user(self: Facility, user_id: int, session: scoped_session = None) -> None:
        """Dissociate user from this facility."""
        session = session or db.write
        try:
            User.from_id(user_id, session)  # checks for User.NotFound
            for mapping in session.query(FacilityMap).filter(FacilityMap.user_id == user_id,
                                                             FacilityMap.facility_id == self.id):
                session.delete(mapping)
                session.commit()
            log.info(f'Dissociated facility ({self.id}) from user ({user_id})')
        except Exception:
            session.rollback()
            raise

    @classmethod
    def delete(cls: Type[Facility], facility_id: int, session: scoped_session = None) -> None:
        """Cascade delete to FacilityMap."""
        session = session or db.write
        try:
            facility = cls.from_id(facility_id, session)
            for mapping in session.query(FacilityMap).filter(FacilityMap.facility_id == facility_id):
                session.delete(mapping)
                session.commit()
                log.info(f'Dissociated facility ({facility_id}) from user ({mapping.user_id})')
            session.delete(facility)
            session.commit()
            log.info(f'Deleted facility ({facility_id})')
        except Exception:
            session.rollback()
            raise


class FacilityMap(Entity):
    """Mapping table between users and facilities."""

    user_id: Mapped[int] = mapped_column('user_id', INTEGER, ForeignKey(User.id, ondelete='cascade'),
                                         primary_key=True, nullable=False)
    facility_id: Mapped[int] = mapped_column('facility_id', INTEGER, ForeignKey(Facility.id, ondelete='cascade'),
                                             primary_key=True, nullable=False)

    columns = {
        'user_id': int,
        'facility_id': int
    }

    @classmethod
    def from_id(cls: Type[FacilityMap], id: int, session: scoped_session = None) -> FacilityMap:
        raise NotImplementedError()

    @classmethod
    def add(cls: Type[FacilityMap], data: dict, session: scoped_session = None) -> Optional[int]:
        raise NotImplementedError()

    @classmethod
    def delete(cls: Type[FacilityMap], id: int, session: scoped_session = None) -> None:
        raise NotImplementedError()

    @classmethod
    def update(cls: Type[FacilityMap], id: int, session: scoped_session = None, **data) -> None:
        raise NotImplementedError()


# New credentials will be initialized with this level unless otherwise specified
DEFAULT_CLIENT_LEVEL: Final[int] = 10


class Client(Entity):
    """Stores user authorization and authentication."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    user_id: Mapped[int] = mapped_column('user_id', INTEGER, ForeignKey(User.id), unique=True, nullable=False)
    level: Mapped[int] = mapped_column('level', INTEGER, nullable=False)
    key: Mapped[str] = mapped_column('key', STRING_16, unique=True, nullable=False)
    secret: Mapped[str] = mapped_column('secret', STRING_64, nullable=False)
    valid: Mapped[bool] = mapped_column('valid', BOOLEAN, nullable=False)
    created: Mapped[datetime] = mapped_column('created', DATETIME, nullable=False, server_default=func.now())

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
    def from_key(cls: Type[Client], key: str, session: scoped_session = None) -> Client:
        """Query by unique `key`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.key == key).one()  # noqa
        except NoResultFound as error:
            raise Client.NotFound(f'No client with key={key}') from error

    @classmethod
    def from_user(cls: Type[Client], user_id: int, session: scoped_session = None) -> Client:
        """Query by unique `user_id`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.user_id == user_id).one()  # noqa
        except NoResultFound as error:
            raise Client.NotFound(f'No client with user_id={user_id}') from error

    @classmethod
    def new(cls: Type[Client],
            user_id: int,
            level: int = DEFAULT_CLIENT_LEVEL,
            session: scoped_session = None,
            ) -> Tuple[Key, Secret, Client]:
        """Create client credentials for `user_id` with `level`."""
        session = session or db.write
        try:
            user = User.from_id(user_id, session)
            key, secret = Key.generate(), Secret.generate()
            client = Client(user_id=user_id, level=level, key=key.value, secret=secret.hashed().value, valid=True)
            session.add(client)
            session.commit()
            log.info(f'Added client for user ({user.id})')
            return key, secret, client
        except Exception:
            session.rollback()
            raise

    @classmethod
    def new_secret(cls: Type[Client],
                   user_id: int,
                   session: scoped_session = None) -> Tuple[Key, Secret]:
        """Generate a new secret (store the hashed value)."""
        session = session or db.write
        try:
            client = Client.from_user(user_id, session)
            secret = Secret.generate()
            client.secret = secret.hashed().value
            session.commit()
            log.info(f'Updated client secret for user ({client.user_id})')
            return Key(client.key), secret
        except Exception:
            session.rollback()
            raise

    @classmethod
    def new_key(cls: Type[Client],
                user_id: int,
                session: scoped_session = None) -> Tuple[Key, Secret]:
        """Generate a new key and secret (store the hashed value)."""
        session = session or db.write
        try:
            client = Client.from_user(user_id, session)
            key, secret = Key.generate(), Secret.generate()
            client.key = key.value
            client.secret = secret.hashed().value
            session.commit()
            log.info(f'Updated client key and secret for user ({client.user_id})')
            return key, secret
        except Exception:
            session.rollback()
            raise


# New session tokens if not otherwise requested will have the following lifetime (seconds)
DEFAULT_EXPIRE_TIME: Final[int] = 900  # i.e., 15 minutes


class Session(Entity):
    """Session stores hashed token with claim details."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    client_id: Mapped[int] = mapped_column('client_id', INTEGER, ForeignKey(Client.id, ondelete='cascade'),
                                           unique=True, nullable=False)
    expires: Mapped[datetime] = mapped_column('expires', DATETIME, nullable=True)  # NULL is no-expiration!
    token: Mapped[str] = mapped_column('token', STRING_64, nullable=False)
    created: Mapped[datetime] = mapped_column('created', DATETIME, nullable=False, server_default=func.now())

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
    def from_client(cls: Type[Session], client_id: int, session: scoped_session = None) -> Session:
        """Query by unique client `id`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.client_id == client_id).one()  # noqa
        except NoResultFound as error:
            raise Session.NotFound(f'No session with client_id={client_id}') from error

    @classmethod
    def new(cls: Type[Session],
            user_id: int,
            expires: Optional[Union[float, timedelta]] = DEFAULT_EXPIRE_TIME,
            session: scoped_session = None) -> JWT:
        """Create new session for `user`."""
        session = session or db.write
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
            old.created = datetime.now().astimezone()
            session.commit()
        except Session.NotFound:
            new = Session(client_id=client.id, expires=jwt.exp, token=token)
            session.add(new)
            session.commit()
        log.info(f'Created session for user ({user_id})')
        return jwt


class ObjectType(Entity):
    """Stores object types (e.g., 'SNIa')."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ObjectType."""

    @classmethod
    def from_name(cls: Type[ObjectType], name: str, session: scoped_session = None) -> ObjectType:
        """Query by unique object_type `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise ObjectType.NotFound(f'No object_type with name={name}') from error

    @classmethod
    def get_or_create(cls: Type[ObjectType],
                      name: str,
                      session: scoped_session = None) -> ObjectType:
        """Get or create object_type for a given `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound:
            return cls.add({'name': name, 'description': f'{name} (automatically created)'}, session or db.write)


# Object name provider pattern matching
OBJECT_NAMING_PATTERNS: Final[Dict[str, re.Pattern]] = {
    'id': re.compile(r'^[0-9]+$'),
    'ztf': re.compile(r'^ZTF.*'),
    'iau': re.compile(r'^20[2-3][0-9][a-zA-Z]+'),
    'antares': re.compile(r'^ANT.*'),
    'atlas': re.compile(r'^ATLAS.*'),
    'tag': re.compile(r'^[a-z]+_[a-z]+_[a-z]'),
}


class Object(Entity):
    """Stores object."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    type_id: Mapped[int] = mapped_column('type_id', INTEGER, ForeignKey(ObjectType.id), nullable=True)
    pred_type: Mapped[dict] = mapped_column('pred_type', JSON, nullable=False, default={})
    aliases: Mapped[dict] = mapped_column('aliases', JSON, nullable=False, default={})
    ra: Mapped[float] = mapped_column('ra', FLOAT, nullable=False)
    dec: Mapped[float] = mapped_column('dec', FLOAT, nullable=False)
    redshift: Mapped[float] = mapped_column('redshift', FLOAT, nullable=True)
    history: Mapped[dict] = mapped_column('history', JSON, nullable=False, default={})
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False, default={})

    type = relationship(ObjectType, foreign_keys=[type_id, ])

    relationships = {'type': ObjectType}
    columns = {
        'id': int,
        'type_id': int,
        'pred_type': dict,
        'aliases': dict,
        'ra': float,
        'dec': float,
        'redshift': float,
        'history': dict,
        'data': dict,
    }

    # store patterns with object class
    name_patterns = OBJECT_NAMING_PATTERNS

    class NotFound(NotFound):
        """NotFound exception specific to Object."""

    @classmethod
    def from_alias(cls: Type[Object], session: scoped_session = None, **alias: str) -> Object:
        """Query by named field in `aliases`."""
        if len(alias) == 1:
            (provider, name), = alias.items()
        else:
            raise AttributeError(f'Expected single named alias')
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (  # noqa
                # NOTE: .op() is the best we can do for now
                (session or db.read).query(Object)
                .filter(Object.aliases.op('->>')(provider) == name)
                .one()
            )
        except NoResultFound as error:
            raise Object.NotFound(f'No object with alias {provider}={name}') from error
        except MultipleResultsFound as error:
            raise NotDistinct(f'Multiple objects with alias {provider}={name}') from error

    @classmethod
    def from_name(cls: Type[Object], name: str, session: scoped_session = None) -> Object:
        """Smart detection of alias by name syntax."""
        for provider, pattern in OBJECT_NAMING_PATTERNS.items():
            if pattern.match(name):
                if provider == 'id':
                    return cls.from_id(int(name), session or db.read)
                else:
                    return cls.from_alias(**{provider: name, 'session': session or db.read})
        else:
            raise Object.NotFound(f'Unrecognized name pattern \'{name}\'')

    @classmethod
    def add_alias(cls: Type[Object],
                  object_id: int,
                  session: scoped_session = None,
                  **aliases: str) -> None:
        """Add alias(es) to the given object."""
        session = session or db.write
        try:
            obj = cls.from_id(object_id, session)
            for provider, name in aliases.items():
                try:
                    existing = cls.from_alias(**{provider: name, 'session': session})
                    if existing.id != object_id:
                        raise AlreadyExists(f'Object with alias {provider}={name} already exists')
                except Object.NotFound:
                    obj.aliases = {**obj.aliases, provider: name}
                    session.commit()
        except Exception:
            session.rollback()
            raise


class ObservationType(Entity):
    """Stores observation type (e.g., 'g-ztf')."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    units: Mapped[str] = mapped_column('units', TEXT, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)

    columns = {
        'id': int,
        'name': str,
        'units': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ObservationType."""

    @classmethod
    def from_name(cls: Type[ObservationType],
                  name: str,
                  session: scoped_session = None) -> ObservationType:
        """Query by unique observation_type `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise ObservationType.NotFound(f'No observation_type with name={name}') from error


class SourceType(Entity):
    """Stores observation source type (e.g., 'broker')."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to SourceType."""

    @classmethod
    def from_name(cls: Type[SourceType], name: str, session: scoped_session = None) -> SourceType:
        """Query by unique source_type `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise SourceType.NotFound(f'No source_type with name={name}') from error


class Source(Entity):
    """Stores observation source (e.g., 'antares')."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    type_id: Mapped[int] = mapped_column('type_id', INTEGER, ForeignKey(SourceType.id), nullable=False)
    facility_id: Mapped[int] = mapped_column('facility_id', INTEGER, ForeignKey(Facility.id), nullable=True)
    user_id: Mapped[int] = mapped_column('user_id', INTEGER, ForeignKey(User.id), nullable=True)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False, default={})

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
    def from_name(cls: Type[Source], name: str, session: scoped_session = None) -> Source:
        """Query by unique source `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Source.NotFound(f'No source with name={name}') from error

    @classmethod
    def from_facility(cls: Type[Source],
                      facility_id: int,
                      session: scoped_session = None) -> List[Source]:
        """Query by source `facility_id`."""
        # NOTE: issue with type checking incorrectly infers return type
        return (session or db.read).query(cls).filter(cls.facility_id == facility_id).all()  # noqa

    @classmethod
    def from_user(cls: Type[Source],
                  user_id: int,
                  session: scoped_session = None) -> List[Source]:
        """Query by source `user_id`."""
        # NOTE: issue with type checking incorrectly infers return type
        return (session or db.read).query(cls).filter(cls.user_id == user_id).all()  # noqa

    @classmethod
    def get_or_create(cls: Type[Source],
                      user_id: int,
                      facility_id: int,
                      session: scoped_session = None) -> Source:
        """Fetch or create a new source for a `user_id`, `facility_id` pair."""
        session = session or db.write
        user = User.from_id(user_id, session)
        facility = Facility.from_id(facility_id, session)
        user_name = user.alias.lower().replace(' ', '_').replace('-', '_')
        facility_name = facility.name.lower().replace(' ', '_').replace('-', '_')
        source_name = f'{user_name}_{facility_name}'
        try:
            session.query(FacilityMap).filter_by(user_id=user_id, facility_id=facility_id).one()
        except NoResultFound:
            log.warning(f'Facility ({facility_id}) not associated with user ({user_id})')
        try:
            return Source.from_name(source_name, session)
        except Source.NotFound:
            data = {'type_id': SourceType.from_name('observer', session).id,
                    'user_id': user_id, 'facility_id': facility_id, 'name': source_name,
                    'description': f'Observer (user={user.alias}, facility={facility.name})'}
            return Source.add(data, session)


class Epoch(Entity):
    """Stores epoch."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    created: Mapped[datetime] = mapped_column('created', DATETIME, nullable=False, server_default=func.now())

    columns = {
        'id': int,
        'created': datetime
    }

    class NotFound(NotFound):
        """NotFound exception specific to Epoch."""

    @classmethod
    def new(cls: Type[Epoch], session: scoped_session = None) -> Epoch:
        """Create and return a new epoch."""
        return cls.add({}, session or db.write)

    @classmethod
    def latest(cls: Type[Epoch], session: scoped_session = None) -> Epoch:
        """Get the most recent epoch."""
        # NOTE: issue with type checking incorrectly infers return type
        return (session or db.read).query(cls).order_by(cls.id.desc()).first()  # noqa

    @classmethod
    def select(cls: Type[Epoch],
               limit: int,
               offset: int = 0,
               session: scoped_session = None) -> List[Epoch]:
        """Select a range of epochs."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read)
            .query(cls)
            .order_by(cls.id.desc())
            .filter(cls.id <= cls.latest(session).id - offset)
            .limit(limit)
            .all()
        )


class Observation(Entity):
    """Observation table."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True, nullable=False)
    epoch_id: Mapped[int] = mapped_column('epoch_id', INTEGER, ForeignKey(Epoch.id), nullable=False)
    type_id: Mapped[int] = mapped_column('type_id', INTEGER, ForeignKey(ObservationType.id), nullable=False)
    object_id: Mapped[int] = mapped_column('object_id', INTEGER, ForeignKey(Object.id), nullable=False)
    source_id: Mapped[int] = mapped_column('source_id', INTEGER, ForeignKey(Source.id), nullable=False)
    value: Mapped[float] = mapped_column('value', FLOAT, nullable=True)  # NOTE: null value is 'provisional' observation
    error: Mapped[float] = mapped_column('error', FLOAT, nullable=True)
    time: Mapped[datetime] = mapped_column('time', DATETIME, nullable=False)
    recorded: Mapped[datetime] = mapped_column('recorded', DATETIME, nullable=False, server_default=func.now())

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
    def from_object(cls: Type[Observation],
                    object_id: int,
                    session: scoped_session = None) -> List[Observation]:
        """Query all observations with `object_id`."""
        # NOTE: issue with type checking incorrectly infers return type
        return (session or db.read).query(cls).order_by(cls.id).filter(cls.object_id == object_id).all()  # noqa

    @classmethod
    def from_source(cls: Type[Observation],
                    source_id: int,
                    session: scoped_session = None) -> List[Observation]:
        """All observations with `source_id`."""
        # NOTE: issue with type checking incorrectly infers return type
        return (session or db.read).query(cls).order_by(cls.id).filter(cls.source_id == source_id).all()  # noqa

    def models(self: Observation, session: scoped_session = None) -> List[Model]:
        """Models associated with the current observation and 'epoch_id'."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read)
            .query(Model)
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


class Alert(Entity):
    """Stores broker alert records."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True, nullable=False)
    epoch_id: Mapped[int] = mapped_column('epoch_id', INTEGER, ForeignKey(Epoch.id), nullable=False)
    observation_id: Mapped[int] = mapped_column('observation_id', BIG_INTEGER,
                                                ForeignKey(Observation.id), unique=True, nullable=False)
    data: Mapped[int] = mapped_column('data', JSON, nullable=False)

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
    def from_observation(cls: Type[Alert],
                         observation_id: int,
                         session: scoped_session = None) -> Alert:
        """Query by unique alert `observation_id`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.observation_id == observation_id).one()  # noqa
        except NoResultFound as error:
            raise Alert.NotFound(f'No alert with observation_id={observation_id}') from error


class FileType(Entity):
    """Stores file type data."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to FileType."""

    @classmethod
    def from_name(cls: Type[FileType], name: str, session: scoped_session = None) -> FileType:
        """Query by unique file_type `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise FileType.NotFound(f'No file_type with name={name}') from error

    @classmethod
    def all_names(cls: Type[FileType], session: scoped_session = None) -> List[str]:
        """All names of currently available file_type.name values."""
        return [f.name for f in (session or db.read).query(cls).all()]


class File(Entity):
    """Stores file data as raw bytes."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True, nullable=False)
    epoch_id: Mapped[int] = mapped_column('epoch_id', INTEGER, ForeignKey(Epoch.id), nullable=False)
    observation_id: Mapped[int] = mapped_column('observation_id', BIG_INTEGER,
                                                ForeignKey(Observation.id), unique=True, nullable=False)
    type_id: Mapped[int] = mapped_column('type_id', INTEGER, ForeignKey(FileType.id), nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, nullable=False)
    data: Mapped[bytes] = mapped_column('data', BINARY, nullable=False)

    epoch = relationship(Epoch, backref='file')
    type = relationship(FileType, backref='file')
    observation = relationship(Observation, backref='file')

    relationships = {'epoch': Epoch, 'type': FileType, 'observation': Observation, }
    columns = {
        'id': int,
        'epoch_id': int,
        'observation_id': int,
        'type_id': int,
        'name': str,
        'data': bytes,
    }

    class NotFound(NotFound):
        """NotFound exception specific to File."""

    @classmethod
    def from_observation(cls: Type[File],
                         observation_id: int,
                         session: scoped_session = None) -> File:
        """Query by unique file `observation_id`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.observation_id == observation_id).one()  # noqa
        except NoResultFound as error:
            raise File.NotFound(f'No file with observation_id={observation_id}') from error


class ModelType(Entity):
    """Store model types."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)
    description: Mapped[str] = mapped_column('description', TEXT, nullable=False)

    columns = {
        'id': int,
        'name': str,
        'description': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to ModelType."""

    @classmethod
    def from_name(cls: Type[ModelType], name: str, session: scoped_session = None) -> ModelType:
        """Query by unique model_type `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
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
        """Convert to dictionary (consistent with other `Entity` types)."""
        return {'id': self.id, 'epoch_id': self.epoch_id,
                'type_id': self.type_id, 'observation_id': self.observation_id}


class Model(Entity):
    """Store model data."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True, nullable=False)
    epoch_id: Mapped[int] = mapped_column('epoch_id', INTEGER, ForeignKey(Epoch.id), nullable=False)
    type_id: Mapped[int] = mapped_column('type_id', INTEGER, ForeignKey(ModelType.id), nullable=False)
    observation_id: Mapped[int] = mapped_column('observation_id', BIG_INTEGER,
                                                ForeignKey(Observation.id), nullable=False)
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False)

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

    @classmethod
    def from_object(cls: Type[Model],
                    object_id: int,
                    epoch_id: int = None,
                    session: scoped_session = None) -> List[Model]:
        """Query models for the given object and epoch."""
        query = (session or db.read).query(Model).join(Observation)
        query = query.filter(Observation.object_id == object_id)
        if epoch_id is not None:
            query = query.filter(cls.epoch_id == epoch_id)
        # NOTE: issue with type checking incorrectly infers return type
        return query.all()  # noqa


class RecommendationTag(Entity):
    """Recommendation tag table."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True, nullable=False)
    object_id: Mapped[int] = mapped_column('object_id', INTEGER, ForeignKey(Object.id), unique=True, nullable=False)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=True)

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
    def from_name(cls: Type[RecommendationTag],
                  name: str,
                  session: scoped_session = None) -> RecommendationTag:
        """Query by unique recommendation_tag `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise RecommendationTag.NotFound(f'No recommendation_tag with name={name}') from error

    @classmethod
    def get_or_create(cls: Type[RecommendationTag],
                      object_id: int,
                      session: scoped_session = None) -> RecommendationTag:
        """Get or create recommendation tag for `object_id`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.object_id == object_id).one()  # noqa
        except NoResultFound:
            return cls.new(object_id, session or db.write)

    @classmethod
    def new(cls: Type[RecommendationTag],
            object_id: int,
            session: scoped_session = None) -> RecommendationTag:
        """Create a new recommendation tag for `object_id`."""
        # NOTE: The tag.name is Nullable at first because we have to first commit
        # the tag to get its tag.id because that's what we use to slice into the names list.
        session = session or db.write
        tag = cls.add({'object_id': object_id}, session)
        session.commit()  # NOTE: we have to commit to get the pkey
        tag.name = cls.get_name(tag.id)
        Object.add_alias(object_id, **{'tag': tag.name, 'session': session})
        return tag

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
    def get_name(cls: Type[RecommendationTag], tag_id: int) -> str:
        """Slice into ordered sequence of names."""
        names = cls.build_names()
        return names[tag_id]  # NOTE: will fail when we pass ~2.5M recommended objects


class QueryMethod(Protocol):
    """Function call signature for recommendation query modes."""
    def __call__(self,
                 user_id: int,
                 epoch_id: int = None,
                 limit: int = None,
                 facility_id: int = None,
                 limiting_magnitude: int = None,
                 session: scoped_session = None) -> List[Recommendation]: ...


class Recommendation(Entity):
    """Recommendation table."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True, nullable=False)
    epoch_id: Mapped[int] = mapped_column('epoch_id', INTEGER, ForeignKey(Epoch.id), nullable=False)
    tag_id: Mapped[int] = mapped_column('tag_id', INTEGER, ForeignKey(RecommendationTag.id), nullable=False)
    time: Mapped[datetime] = mapped_column('time', DATETIME, nullable=False, server_default=func.now())
    priority: Mapped[int] = mapped_column('priority', INTEGER, nullable=False)
    object_id: Mapped[int] = mapped_column('object_id', INTEGER, ForeignKey(Object.id), nullable=False)
    facility_id: Mapped[int] = mapped_column('facility_id', INTEGER, ForeignKey(Facility.id), nullable=False)
    user_id: Mapped[int] = mapped_column('user_id', INTEGER, ForeignKey(User.id), nullable=False)
    predicted_observation_id: Mapped[int] = mapped_column('predicted_observation_id', BIG_INTEGER,
                                                          ForeignKey(Observation.id), nullable=True)
    observation_id: Mapped[int] = mapped_column('observation_id', BIG_INTEGER,
                                                ForeignKey(Observation.id), nullable=True)
    accepted: Mapped[bool] = mapped_column('accepted', BOOLEAN, nullable=False, default=False)
    rejected: Mapped[bool] = mapped_column('rejected', BOOLEAN, nullable=False, default=False)
    data: Mapped[dict] = mapped_column('data', JSON, nullable=False, default={})

    epoch = relationship(Epoch, backref='recommendation')
    tag = relationship(RecommendationTag, backref='recommendation')
    user = relationship(User, backref='recommendation')
    facility = relationship(Facility, backref='recommendation')
    object = relationship(Object, backref='recommendation')
    predicted = relationship(Observation, foreign_keys=[predicted_observation_id, ])
    observed = relationship(Observation, foreign_keys=[observation_id, ])

    relationships = {
        'epoch': Epoch,
        'tag': RecommendationTag,
        'user': User,
        'facility': Facility,
        'object': Object,
        'predicted': Observation,
        'observed': Observation,
    }

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

    def model_info(self: Recommendation, session: scoped_session = None) -> List[ModelInfo]:
        """Listing of available models for this recommendation without the data itself."""
        return [
            ModelInfo(id, epoch_id, type_id, observation_id)
            for id, epoch_id, type_id, observation_id in (
                (session or db.read)
                .query(Model.id, Model.epoch_id, Model.type_id, Model.observation_id)
                .order_by(Model.type_id)
                .filter(Model.observation_id == self.predicted_observation_id)
                .all()
            )
        ]

    def models(self: Recommendation, session: scoped_session = None) -> List[Model]:
        """Models associated with the 'predicted_observation_id' and 'epoch_id'."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read)
            .query(Model)
            .order_by(Model.type_id)
            .filter(Model.observation_id == self.predicted_observation_id)
            .all()
        )

    @classmethod
    def from_user(cls: Type[Recommendation],
                  user_id: int,
                  epoch_id: int = None,
                  session: scoped_session = None) -> List[Recommendation]:
        """Query recommendations for the given user and epoch."""
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read)
            .query(cls)
            .order_by(cls.priority)
            .filter(cls.epoch_id == (epoch_id or Epoch.latest(session).id),
                    cls.user_id == user_id)
            .all()
        )

    DEFAULT_QUERY_MODE: str = 'normal'
    QUERY_MODES: List[str] = [
        'normal',
        'realtime',
    ]

    @classmethod
    def _get_query_method(cls: Type[Recommendation], mode: str) -> QueryMethod:
        """Access query method by `mode` name."""
        if mode in cls.QUERY_MODES:
            return getattr(cls, f'_query_{mode}')
        else:
            raise NotImplementedError(f'Recommendation query mode not implemented: {mode}')

    @classmethod
    def next(cls: Type[Recommendation],
             user_id: int,
             epoch_id: int = None,
             limit: int = None,
             mode: str = DEFAULT_QUERY_MODE,
             facility_id: int = None,
             limiting_magnitude: float = None,
             session: scoped_session = None) -> List[Recommendation]:
        """
        Select next recommendation(s) for the given user and epoch, in priority order,
        that has neither been 'accepted' nor 'rejected', up to some `limit`.

        If `facility_id` is provided, only recommendations for the given facility are returned.
        If `limiting_magnitude` is provided, only recommendations with a 'predicted' magnitude
        brighter than this value are returned.
        """
        query_method = cls._get_query_method(mode)
        return query_method(user_id, epoch_id=epoch_id, limit=limit, facility_id=facility_id,
                            limiting_magnitude=limiting_magnitude, session=(session or db.read))

    @classmethod
    def _query_normal(cls: Type[Recommendation],
                      user_id: int,
                      epoch_id: int = None,
                      limit: int = None,
                      facility_id: int = None,
                      limiting_magnitude: float = None,
                      session: scoped_session = None) -> List[Recommendation]:
        """Simple priority ordering."""
        query = cls._base_query(user_id, epoch_id=epoch_id, facility_id=facility_id,
                                limiting_magnitude=limiting_magnitude, session=(session or db.read))
        query = query.order_by(cls.priority)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def _query_realtime(cls: Type[Recommendation],
                        user_id: int,
                        epoch_id: int = None,
                        limit: int = None,
                        facility_id: int = None,
                        limiting_magnitude: float = None,
                        session: scoped_session = None) -> List[Recommendation]:
        """Facility-based 'realtime' ordering, epoch=<latest> always."""
        now = datetime.now().astimezone()
        query = cls._base_query(user_id, epoch_id=epoch_id, facility_id=facility_id,
                                limiting_magnitude=limiting_magnitude, session=(session or db.read))
        targets = []
        for record in query.all():
            try:
                airmass = json.loads(record.data['airmass'])
            except KeyError:
                log.warning(f'Missing airmass for recommendation ({record.id})')
            except Exception as err:
                log.warning(f'Failed to decode airmass data for recommendation ({record.id}): {err}')
            else:
                # Note: converting to datetime first retains TZ-info within dataframe
                df = DataFrame({'time': [datetime.fromisoformat(time) for time in airmass.keys()],
                                'value': airmass.values()})
                prev_df = df.loc[df.time < now]
                next_df = df.loc[df.time > now]
                if prev_df.empty or next_df.empty:
                    log.warning(f'No targets near current time ({now})')
                    continue  # No surrounding timestamps
                else:
                    df = DataFrame([prev_df, next_df])
                    df = df.set_index('time')
                    df = df.reindex(DatetimeIndex([df.iloc[0].time, now, df.iloc[-1].time]))
                    df = df.interpolate()
                    value = abs(df.loc[now].value)
                    if value <= 1.4:  # NOTE: airmass cutoff of 1.4
                        targets.append({'id': record.id, 'airmass': value, 'record': record})

        if not targets:
            log.warning(f'No immediate targets (user={user_id}, facility={facility_id}, epoch={epoch_id})')
            return []

        limit = limit or len(targets)
        targets = DataFrame(targets).sort_values(by='airmass', ascending=True)
        return targets.head(limit).record.to_list()

    @classmethod
    def _base_query(cls: Type[Recommendation],
                    user_id: int,
                    epoch_id: int = None,
                    facility_id: int = None,
                    limiting_magnitude: float = None,
                    session: scoped_session = None) -> Query:
        """Build base recommendation query."""
        # NOTE: we have to join on predicted_observation_id <- observation.id if we want to make a
        #       comparison to limiting_magnitude, but we will now allow recommendations without an
        #       explicit prediction. The join will filter out these rows, so we will only do it if
        #       limiting_magnitude is requested
        session = session or db.read
        if limiting_magnitude:
            predicted = aliased(Observation)
            query = session.query(cls).join(predicted, cls.predicted_observation_id == predicted.id)
            query = query.filter(predicted.value <= limiting_magnitude)
        else:
            query = session.query(cls)
        query = query.filter(cls.user_id == user_id)
        query = query.filter(cls.epoch_id == (epoch_id or Epoch.latest(session).id))
        query = query.filter(cls.accepted.is_(False))
        query = query.filter(cls.rejected.is_(False))
        if facility_id is not None:
            query = query.filter(cls.facility_id == facility_id)
        return query

    @classmethod
    def history(cls,
                user_id: int,
                epoch_id: int,
                session: scoped_session = None) -> List[Recommendation]:
        """
        Select previous recommendations that the user has either affirmatively
        accepted OR rejected.
        """
        # NOTE: issue with type checking incorrectly infers return type
        return (  # noqa
            (session or db.read)
            .query(cls)
            .order_by(cls.id)
            .filter(cls.user_id == user_id)
            .filter(cls.epoch_id == epoch_id)
            .filter(or_(cls.accepted.is_(True), cls.rejected.is_(True)))
            .all()
        )


# indices for recommendation table
recommendation_object_index = Index('recommendation_object_index', Recommendation.object_id)
recommendation_user_facility_index = Index('recommendation_user_facility_index',
                                           Recommendation.user_id, Recommendation.facility_id)
recommendation_epoch_user_index = Index('recommendation_epoch_user_index',
                                        Recommendation.epoch_id, Recommendation.user_id)


# ----------------------------------------------------------------------------------------------
# Re-implementation of StreamKit models
# We conform to the database schema but re-define under a common ModelInterface


class Level(Entity):
    """A level relates a name and its identifier."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Level."""

    @classmethod
    def from_name(cls, name: str, session: scoped_session = None) -> Level:
        """Query by unique level `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Level.NotFound(f'No level with name={name}') from error


class Topic(Entity):
    """A topic relates a name and its identifier."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Topic."""

    @classmethod
    def from_name(cls, name: str, session: scoped_session = None) -> Topic:
        """Query by unique topic `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Topic.NotFound(f'No topic with name={name}') from error


class Host(Entity):
    """A host relates a name and its identifier."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Host."""

    @classmethod
    def from_name(cls, name: str, session: scoped_session = None) -> Host:
        """Query by unique host `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Host.NotFound(f'No host with name={name}') from error


class Message(Entity):
    """A message joins topic, level, and host, with timestamp and an identifier for the message."""

    id: Mapped[int] = mapped_column('id', BIG_INTEGER, primary_key=True)
    time: Mapped[datetime] = mapped_column('time', DATETIME, nullable=False)
    topic_id: Mapped[int] = mapped_column('topic_id', INTEGER, ForeignKey(Topic.id), nullable=False)
    level_id: Mapped[int] = mapped_column('level_id', INTEGER, ForeignKey(Level.id), nullable=False)
    host_id: Mapped[int] = mapped_column('host_id', INTEGER, ForeignKey(Host.id), nullable=False)
    text: Mapped[str] = mapped_column('text', TEXT, nullable=False)

    # NOTE: conditionally redefine for time-based partitioning
    # if config.provider in ('timescale', ):
    #     # The primary key is (`time`, `topic_id`) NOT `id`.
    #     # This is weird but important for automatic hyper-table partitioning
    #     # on the `time` values for TimeScaleDB (PostgreSQL).
    #     id = Column('id', BigInteger(),
    #                 Sequence('message_id_seq', start=1, increment=1, schema=schema),
    #                 CheckConstraint('id > 0', name='message_id_check'), nullable=False)
    #     time = Column('time', DateTime(timezone=True), nullable=False, primary_key=True)
    #     topic_id = Column('topic_id', Integer(), nullable=False, primary_key=True)

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


# if config.provider in ('timescale', ):
#     # NOTE: we use time-topic PK and need to index ID
#     message_id_index = Index('message_id_index', Message.id)
#     message_time_topic_index = None
# else:
message_id_index = None
message_time_topic_index = Index('message_time_topic_index', Message.time, Message.topic_id)


class Subscriber(Entity):
    """A subscriber relates a name and its identifier."""

    id: Mapped[int] = mapped_column('id', INTEGER, primary_key=True)
    name: Mapped[str] = mapped_column('name', TEXT, unique=True, nullable=False)

    columns = {
        'id': int,
        'name': str
    }

    class NotFound(NotFound):
        """NotFound exception specific to Subscriber."""

    @classmethod
    def from_name(cls, name: str, session: scoped_session = None) -> Subscriber:
        """Query by unique subscriber `name`."""
        try:
            # NOTE: issue with type checking incorrectly infers return type
            return (session or db.read).query(cls).filter(cls.name == name).one()  # noqa
        except NoResultFound as error:
            raise Subscriber.NotFound(f'No subscriber with name={name}') from error


class Access(Entity):
    """Access tracks the last message received on a given topic for a given subscriber."""

    subscriber_id: Mapped[int] = mapped_column('subscriber_id', INTEGER, ForeignKey(Subscriber.id),
                                               nullable=False, primary_key=True)
    topic_id: Mapped[int] = mapped_column('topic_id', INTEGER, ForeignKey(Topic.id), nullable=False, primary_key=True)
    time: Mapped[datetime] = mapped_column('time', DATETIME, nullable=False)

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
tables: Dict[str, Type[Entity]] = {
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
indices: Dict[str, Index] = {'recommendation_object_index': recommendation_object_index,
                             'recommendation_epoch_user_index': recommendation_epoch_user_index,
                             'recommendation_user_facility_index': recommendation_user_facility_index,
                             'observation_time_index': observation_time_index,
                             'observation_object_index': observation_object_index,
                             'observation_recorded_index': observation_recorded_index,
                             'observation_source_object_index': observation_source_object_index,
                             'message_time_topic_index': message_time_topic_index}


# optionally defined depending on provider
# if config.provider in ('timescale', ):
#     indices['message_id_index'] = message_id_index
# else:
