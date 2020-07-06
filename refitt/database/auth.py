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

"""User/identity authorization management for REST api."""

# type annotations
from __future__ import annotations
from typing import Dict, TypeVar, Optional, Union, Any

# standard libs
import re
import json
import string
import random
import hashlib
import functools
from datetime import datetime, timedelta

# external libs
from pandas import Timestamp
from cryptography.fernet import Fernet, InvalidToken

# internal libs
from ..core.config import config, expand_parameters, ConfigurationError
from ..core.logging import Logger
from .core.interface import execute, Interface, Table, Record, RecordNotFound


# initialize module level logger
log = Logger(__name__)


# interface
client = Table('auth', 'client')
access = Table('auth', 'access')


class AuthError(Exception):
    """Base class for authentication/authorization errors."""


class ClientNotFound(RecordNotFound):
    """The client credentials were not found."""


class TokenNotFound(RecordNotFound):
    """The access token was not found."""


class ClientInvalid(AuthError):
    """The client credentials have been invalidated."""


class ClientInsufficient(AuthError):
    """The client authorization level is too low."""


# piggy back on cryptography
class TokenInvalid(AuthError):
    """The token is not legitimate."""


class TokenExpired(AuthError):
    """The token's expiration date is come to pass."""


class Cipher:
    """A Fernet cipher manager."""

    _fernet: Fernet = None

    def __init__(self, key: bytes) -> None:
        """Initialize cipher with given root `key`."""
        self._fernet = Fernet(key)

    @classmethod
    @functools.lru_cache(maxsize=None)
    def from_config(cls) -> Cipher:
        """Load the root key from the configuration."""
        try:
            api_config = config['api']
        except KeyError:
            raise ConfigurationError('"api" section missing')
        root_key = expand_parameters('root_key', api_config)
        if root_key is None:
            raise ConfigurationError('no root_key found')
        return cls(root_key.encode())

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt `data` with the Cipher."""
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt `data` with the Cipher."""
        return self._fernet.decrypt(data)


class CryptoDigits:
    """Generate and represent sensitive cryptographic strings."""

    # instance variables
    _size: int = None
    _value: str = None
    _is_hash: bool = False

    # customizable derived class attributes
    _digits: str = string.ascii_letters + string.digits + '-_='
    _pattern: re.Pattern = re.compile(r'^[a-zA-Z0-9-_=]+$')
    _hash_alg: str = 'sha256'

    def __init__(self, value: Union[str, CryptoDigits]) -> None:
        """Direct initialization with `value`."""

        # allow passive coercion
        if isinstance(value, CryptoDigits):
            self._size = len(value)
            self.value = value.value
            self.is_hash = value.is_hash
            return

        # NOTE: derived classes will have set a _size and this enforces initialization
        # The base class will simply define this on the fly if needed.
        self._size = self._size if self._size is not None else len(value)
        self.value = value

    @property
    def value(self) -> str:
        """Access the underlying hex digits."""
        return self._value

    @value.setter
    def value(self, other: str) -> None:
        """Set the underlying hex digits."""
        if not isinstance(other, str):
            raise TypeError(f'{self.__class__.__name__}.value expects type str, given {type(other)}.')
        if len(other) != self._size:
            raise ValueError(f'{self.__class__.__name__}.value expects {self._size} digits.')
        if self._pattern.match(other) is None:
            raise ValueError(f'{self.__class__.__name__}.value must match {self._pattern}.')
        self._value = other

    def __len__(self) -> int:
        return self._size

    def __str__(self) -> str:
        """Masked view of the hexdigits."""
        if self._size < 9:
            return self.value[0] + '...' + self.value[-1]
        else:
            return self.value[:3] + '...' + self.value[-3:]

    def __repr__(self) -> str:
        """Interactive representation. See `__str__`."""
        if self.is_hash:
            return f'<{self.__class__.__name__}[hashed](\'{self}\')>'
        else:
            return f'<{self.__class__.__name__}(\'{self}\')>'

    def copy(self) -> CryptoDigits:
        """Return a copy."""
        new = self.__class__(self.value)
        new._is_hash = self._is_hash
        return new

    @classmethod
    def generate(cls, size: int = None) -> CryptoDigits:
        """Generate a new instance of `size`."""
        _size = size if size is not None else cls._size
        if _size is not None:
            digits = (random.SystemRandom().choice(cls._digits) for i in range(_size))
            return cls(''.join(digits))
        else:
            raise AttributeError(f'{cls.__name__}.generate needs a size if not intrinsic.')

    @staticmethod
    def _hashed(value: str, method: str = 'sha256') -> str:
        return getattr(hashlib, method)(value.encode()).hexdigest()

    def hashed(self) -> CryptoDigits:
        """Return HexDigits as a hash of the previous."""
        digits = self.copy()
        if self.is_hash:
            return digits
        else:
            hashed_digits = self._hashed(self.value, self._hash_alg)
            digits._size = len(hashed_digits)  # depends on algorithm
            digits._value = hashed_digits
            digits._is_hash = True
            return digits

    @property
    def is_hash(self) -> bool:
        """Is this a hash of some other CryptoDigits?"""
        return self._is_hash

    @is_hash.setter
    def is_hash(self, value: bool) -> None:
        """Assign whether this is a hash of some other CryptoDigits."""
        self._is_hash = bool(value)

    def encode(self) -> bytes:
        """JSON-serialize the JWT to bytes."""
        return self.value.encode('utf-8')

    def encrypt(self, cipher: Cipher = None) -> bytes:
        """Encrypt an encoded version of the JWT using a Cipher."""
        _cipher = cipher if cipher is not None else Cipher.from_config()
        return _cipher.encrypt(self.encode())

    @classmethod
    def decrypt(cls, digits: bytes, cipher: Cipher = None) -> CryptoDigits:
        """Decrypt cryptographic `digits`."""
        _cipher = cipher if cipher is not None else Cipher.from_config()
        return cls(_cipher.decrypt(digits).decode())

    def __eq__(self, other: CryptoDigits) -> bool:
        """The underlying digits are the same."""
        return self.hashed().value == self.__class__(other).hashed().value

    def __ne__(self, other: CryptoDigits) -> bool:
        """The underlying digits are different."""
        return not self == other


class Key(CryptoDigits):
    """A 16-digit key."""
    _size = 16


class Secret(CryptoDigits):
    """A 64-digit secret."""
    _size = 64  # sha256 gives the same number of digits


class Token(CryptoDigits):
    """A 64-digit secret."""
    _size = None  # depends on JWT data


# value types for JWT claims
Claim = TypeVar('Claim', int, str)
ExpTime = TypeVar('ExpTime', datetime, timedelta, float, int)


class JWT(Record):
    """
    A JSON Web Token.
    """

    _fields = ('sub', 'exp')
    _sub: int = None
    _exp: Optional[datetime] = None

    # NOTE: we get the behavior we want from Record
    # but we don't have a primary key so we override
    def __init__(self, sub: int, exp: ExpTime) -> None:  # noqa
        """Initialize from `sub` and `exp`."""
        self.sub = sub
        self.exp = exp

    @property
    def sub(self) -> int:
        """The subject claim (client_id)."""
        return self._sub

    @sub.setter
    def sub(self, value: int) -> None:
        """Set the subject claim (client_id)."""
        self._sub = int(value)

    @property
    def exp(self) -> Optional[datetime]:
        """The expiration date claim (Unix time)."""
        return self._exp

    @exp.setter
    def exp(self, value: ExpTime) -> None:
        """Set the expiration date claim (Unix time)."""
        if value is None or isinstance(value, datetime):
            self._exp = value
        elif isinstance(value, timedelta):
            self._exp = datetime.utcnow() + value
        elif isinstance(value, (int, float)):
            self._exp = None if value == -1 else datetime.fromtimestamp(float(value))
        else:
            raise TypeError(f'{self.__class__.__name__}.exp: unsupported type {type(value)}')

    def __str__(self) -> str:
        """String representation."""
        return f'JWT(sub={repr(self.sub)}, exp={repr(self.exp)})'

    def __repr__(self) -> str:
        """Interactive representation (see also: __str__)."""
        return str(self)

    def encode(self) -> bytes:
        """JSON-serialize the JWT to bytes."""
        payload = self.to_dict()
        payload['exp'] = -1 if self.exp is None else int(self.exp.timestamp())
        return json.dumps(payload).encode('utf-8')

    def encrypt(self, cipher: Cipher = None) -> bytes:
        """Encrypt an encoded version of the JWT using a Cipher."""
        _cipher = cipher if cipher is not None else Cipher.from_config()
        return _cipher.encrypt(self.encode())

    @classmethod
    def decrypt(cls, token: bytes, cipher: Cipher = None) -> JWT:
        """Decrypt a `token` as a new JWT."""
        try:
            _cipher = cipher if cipher is not None else Cipher.from_config()
            payload = json.loads(_cipher.decrypt(token).decode())
            return cls.from_dict(payload)
        except InvalidToken:
            raise TokenInvalid(str(Token(token.decode())))

    @classmethod
    def from_database(cls, *args, **kwargs) -> None:
        raise NotImplementedError('JWT is not directly stored')


_UPDATE_ACCESS = """\
INSERT INTO "auth"."access" (access_id, client_id, access_token, access_expires)
VALUES (:access_id, :client_id, :access_token, :access_expires)
ON CONFLICT (access_id) DO UPDATE
    SET client_id      = excluded.client_id,
        access_token   = excluded.access_token,
        access_expires = excluded.access_expires;
"""


_INSERT_ACCESS = """\
INSERT INTO "auth"."access" (client_id, access_token, access_expires)
VALUES (:client_id, :access_token, :access_expires)
RETURNING access_id;
"""


_REMOVE_ACCESS = """\
DELETE FROM "auth"."access"
WHERE access_id = :access_id;
"""


# New access tokens if not otherwise requested will have
# the following lifetime (hours)
DEFAULT_EXPIRE_TIME = 24


class Access(Record):
    """
    Manage records from the "auth"."access" table.

    Example
    -------
    >>> from refitt.database.auth import Access
    >>> access = Access.from_database(client_id=456)
    >>> access
    <Access(access_id=123, client_id=456, access_token=<Token[hashed](5da...613)>,
            access_expires=datetime.datetime(2020, 4, 21, 18, 4, 55, 224647))>
    """

    _fields = ('access_id', 'client_id', 'access_token', 'access_expires')
    _masked = True

    _access_id: Optional[int] = None
    _client_id: int = None
    _access_token: Token = None
    _access_expires: datetime = None

    _FACTORIES = {'access_id': 'from_id', 'client_id': 'from_client', }

    @property
    def access_id(self) -> Optional[int]:
        return self._access_id

    @access_id.setter
    def access_id(self, value: int) -> None:
        _access_id = None if value is None else int(value)
        if _access_id is not None and _access_id < 0:
            raise ValueError(f'{self.__class__.__name__}.access_id expects positive integer')
        else:
            self._access_id = _access_id

    @property
    def client_id(self) -> Optional[int]:
        return self._client_id

    @client_id.setter
    def client_id(self, value: int) -> None:
        _client_id = int(value)
        if _client_id < 0:
            raise ValueError(f'{self.__class__.__name__}.client_id expects positive integer')
        else:
            self._client_id = _client_id

    @property
    def access_token(self) -> Token:
        return self._access_token

    @access_token.setter
    def access_token(self, value: Token) -> None:
        self._access_token = Token(value)

    @property
    def access_expires(self) -> Optional[datetime]:
        return self._access_expires

    @access_expires.setter
    def access_expires(self, value: Optional[datetime]) -> None:
        if value is None or isinstance(value, datetime):
            self._access_expires = value
        else:
            raise TypeError(f'{self.__class__.__name__}.access_token expects datetime.datetime')

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Access:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            record = super()._from_unique(table, field, value, interface)
            record.access_token.is_hash = True  # noqa (non-member)
            if record.access_expires is not None:
                record.access_expires = record.access_expires.to_pydatetime()  # noqa (non-member)
            return record  # noqa (return type)
        except RecordNotFound as error:
            raise TokenNotFound(*error.args) from error

    @classmethod
    def from_id(cls, access_id: int, interface: Interface = None) -> Access:
        """Get access record from `access_id`."""
        return cls._from_unique(access, 'access_id', access_id, interface)

    @classmethod
    def from_client(cls, client_id: int, interface: Interface = None) -> Access:
        """Get access record from `client_id`."""
        return cls._from_unique(access, 'client_id', client_id, interface)

    @classmethod
    def from_jwt(cls, jwt: JWT, cipher: Cipher = None) -> Access:
        """A JWT (JSON Web Token) contains all necessary information."""
        return cls(client_id=jwt.sub, access_expires=jwt.exp,
                   access_token=Token(jwt.encrypt(cipher=cipher).decode()))

    def hashed(self) -> Access:
        """A copy of the Access record with the token hashed."""
        other = self.copy()
        other.access_token = other.access_token.hashed()
        return other

    def to_database(self) -> int:
        """
        Add record to the "auth"."access" table.
        If `access_id` is known, an update is triggered instead.

        Notes
        -----
        The "access_token" is hashed prior to insertion.

        Example
        -------
        >>> from datetime import timedelta
        >>> from refitt.database.auth import Access, JWT
        >>> token = JWT(sub=456, exp=timedelta(minutes=15))
        >>> record = Access.from_jwt(token)
        >>> record.to_database()
        """
        data = self.hashed().to_dict()
        data['access_token'] = data['access_token'].value
        access_id = data.pop('access_id')
        if access_id:
            execute(_UPDATE_ACCESS, access_id=access_id, **data)
            log.info(f'updated access token (access_id={access_id})')
        else:
            ((access_id, ),) = execute(_INSERT_ACCESS, **data)
            log.info(f'added access token (access_id={access_id})')
        return access_id

    @classmethod
    def new_token(cls, client_id: int, access_expires: ExpTime) -> Access:
        """
        This method ensures the record and the database and the token
        passed to the end-user are synchronized.

        Parameters
        ----------
        client_id: int
            The client_id for the database record.

        access_expires: None, timedelta, datetime, int, float
            The timestamp for when this access expires.

        Returns
        -------
        record: Access
            The generated access record.

        See Also
        --------
        - `.from_jwt`
        - `.JWT`

        Example
        -------
        >>> from datetime import timedelta
        >>> from refitt.database.auth import Access
        >>> record = Access.new_token(456, timedelta(minutes=15))
        >>> record.embed()
        {'client_id': 456',
         'access_token': 'ABC...123',
         'access_expires': '2020-04-22 17:18:38.070327'}
        """
        token = JWT(sub=client_id, exp=access_expires)
        record = cls.from_jwt(token)
        try:
            old = cls._from_unique(access, 'client_id', client_id)
            record.access_id = old.access_id
        except RecordNotFound:
            pass
        record.access_id = record.to_database()
        return record

    def embed(self, cipher: Cipher = None) -> Dict[str, Claim]:
        """Return dictionary representation WITH the token embedded."""
        exp = 'never' if self.access_expires is None else str(self.access_expires)
        return {'client_id': self.client_id,
                'access_token': self.access_token.value,
                'access_expires': exp}

    @classmethod
    def remove(cls, access_id: int) -> None:
        """Purge the access record for `access_id`."""
        execute(_REMOVE_ACCESS, access_id=access_id)


_UPDATE_CLIENT = """\
INSERT INTO "auth"."client" (client_id, user_id, client_level, client_key, client_secret, client_valid, client_created)
VALUES (:client_id, :user_id, :client_level, :client_key, :client_secret, :client_valid, :client_created)
ON CONFLICT (client_id) DO UPDATE
    SET user_id        = excluded.user_id,
        client_level   = excluded.client_level,
        client_key     = excluded.client_key,
        client_secret  = excluded.client_secret,
        client_valid   = excluded.client_valid,
        client_created = excluded.client_created;
"""


_INSERT_CLIENT = """\
INSERT INTO "auth"."client" (user_id, client_level, client_key, client_secret, client_valid, client_created)
VALUES (:user_id, :client_level, :client_key, :client_secret, :client_valid, :client_created)
RETURNING client_id;
"""


_REVOKE_CLIENT = """\
UPDATE "auth"."client"
SET
    client_valid = false
WHERE
    user_id = :user_id;
"""


_REMOVE_CLIENT = """\
DELETE FROM "auth"."client"
WHERE client_id = :client_id;
"""


# New credentials will be initialized with this level unless
# otherwise specified
DEFAULT_CLIENT_LEVEL = 5


class Client(Record):
    """A set of client credentials."""

    _fields = ('client_id', 'user_id', 'client_level', 'client_key',
               'client_secret', 'client_valid', 'client_created')

    _client_id: Optional[int] = None
    _user_id: int = None
    _client_level: int = None
    _client_key: Key = None
    _client_secret: Secret = None
    _client_valid: bool = None
    _client_created: datetime = None

    _FACTORIES = {'client_id': 'from_id', 'client_key': 'from_key',
                  'user_id': 'from_user'}

    @property
    def client_id(self) -> int:
        return self._client_id

    @client_id.setter
    def client_id(self, value: int) -> None:
        _client_id = None if value is None else int(value)
        if _client_id is not None and _client_id < 0:
            raise ValueError(f'{self.__class__.__name__}.client_id expects positive integer')
        else:
            self._client_id = _client_id

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
    def client_level(self) -> int:
        return self._client_level

    @client_level.setter
    def client_level(self, value: int) -> None:
        _client_level = int(value)
        if _client_level < 0:
            raise ValueError(f'{self.__class__.__name__}.client_level expects positive integer')
        else:
            self._client_level = _client_level

    @property
    def client_key(self) -> Key:
        return self._client_key

    @client_key.setter
    def client_key(self, value: Key) -> None:
        self._client_key = Key(value)

    @property
    def client_secret(self) -> Secret:
        return self._client_secret

    @client_secret.setter
    def client_secret(self, value: Secret) -> None:
        self._client_secret = Secret(value)

    @property
    def client_valid(self) -> bool:
        return self._client_valid

    @client_valid.setter
    def client_valid(self, value: bool) -> None:
        self._client_valid = bool(value)

    @property
    def client_created(self) -> datetime:
        return self._client_created

    @client_created.setter
    def client_created(self, value: datetime) -> None:
        _client_created = value
        if not isinstance(_client_created, datetime):
            raise TypeError(f'{self.__class__.__name__}.client_created expects datetime.datetime')
        else:
            self._client_created = _client_created

    @classmethod
    def _from_unique(cls, table: Table, field: str, value: Union[int, str],
                     interface: Interface = None) -> Client:
        """Modified from base implementation to adjust virtual and metadata attributes."""
        try:
            record = super()._from_unique(table, field, value, interface)
            record.client_secret.is_hash = True  # noqa (non-member)
            record.client_created = record.client_created.to_pydatetime()  # noqa (non-member)
            return record  # noqa (return type)
        except RecordNotFound as error:
            raise ClientNotFound(*error.args) from error

    @classmethod
    def from_id(cls, client_id: int, interface: Interface = None) -> Client:
        """Get client credentials for `client_id`."""
        return cls._from_unique(client, 'client_id', client_id, interface)

    @classmethod
    def from_key(cls, client_key: str, interface: Interface = None) -> Client:
        """Get client credentials for `client_key`."""
        return cls._from_unique(client, 'client_key', client_key, interface)

    @classmethod
    def from_user(cls, user_id: int, interface: Interface = None) -> Client:
        """Get client credentials from `user_id`."""
        return cls._from_unique(client, 'user_id', user_id, interface)

    def hashed(self) -> Client:
        """Hash the client_secret."""
        other = self.copy()
        other.client_secret = other.client_secret.hashed()
        return other

    def to_database(self) -> int:
        """
        Add Client to the "auth"."client" table.
        If `client_id` is unknown, an update is triggered instead.

        Notes
        -----
        The "client_secret" string is hashed before insertion!

        Example
        -------
        >>> from refitt.database.auth import Client, Secret
        >>> record = Client.from_id(456)
        >>> record.client_secret = Secret.generate()
        >>> record.to_database()
        """
        data = self.hashed().embed()
        client_id = data.pop('client_id')
        if client_id:
            execute(_UPDATE_CLIENT, client_id=client_id, **data)
            log.info(f'updated client credentials (client_id={client_id})')
        else:
            ((client_id, ),) = execute(_INSERT_CLIENT, **data).fetchall()
            log.info(f'added client credentials (client_id={client_id})')
        if self.client_level == 0:
            log.warning(f'added zero-level credentials (client_id={self.client_id})')
        return client_id

    @classmethod
    def new(cls, user_id: int, client_level: int = DEFAULT_CLIENT_LEVEL) -> Client:
        """
        Generate a key/secret pair and add credentials to the database.

        Parameters
        ----------
        user_id: int
            The unique "user_id" to generate credentials for.

        client_level: int (default: `DEFAULT_CLIENT_LEVEL`)
            A whole number greater than zero.

        Returns
        -------
        client: `Client`
            The generated set of client credentials.

        Notes
        -----
        The generated client_secret is returned as-is. A hashed copy is written
        to the database, but the returned copy is the real secret.

        Example
        -------
        >>> from refitt.database.auth import Client
        >>> Client.new(user_id=345, client_level=2)
        <Client(client_id=234, user_id=345, client_level=2,
                client_key=<Key('ABC...123')>, client_secret=<Secret('DEF...456')>,
                client_created=datetime.datetime(2020, 4, 22, 5, 48, 11, 572350, tzinfo=<UTC>))>
        """
        try:
            old = cls.from_user(user_id)
            record = Client(client_id=old.client_id, user_id=user_id, client_level=old.client_level,
                            client_key=old.client_key, client_secret=Secret.generate(),
                            client_valid=True, client_created=datetime.utcnow())
        except RecordNotFound:
            record = Client(user_id=user_id, client_level=client_level,
                            client_key=Key.generate(), client_secret=Secret.generate(),
                            client_valid=True, client_created=datetime.utcnow())
        client_id = record.to_database()
        record.client_id = client_id
        log.info(f'client credentials updated (client_id={client_id})')
        return record

    @classmethod
    def update(cls, client_id: int, **data) -> None:
        """
        Update specific `data` fields for a specifc set of client credentials.

        Arguments
        ---------
        client_id: int
            The unique "client_id" for the record to be altered.
        **data:
            Specific named parameters to be merged into the record.
            E.g., "client_valid=False".

        See Also
        --------
        `.to_database`: Add/update a set of client credentials.

        Example
        -------
        >>> from refitt.database.auth import Client
        >>> Client.update(456, client_valid=False)
        """
        old = cls.from_database(client_id=client_id)
        new = Client.from_dict({**old.to_dict(), **data})
        new.to_database()

    @classmethod
    def revoke(cls, client_id: int) -> None:
        """
        Set "client_valid" to false in database.

        Arguments
        ---------
        client_id: int
            The client_id for the record to alter.

        Example
        -------
        >>> from refitt.database.auth import Client
        >>> Client.revoke(456)
        """
        execute(_REVOKE_CLIENT, client_id=client_id)
        log.debug(f'client credentials revoked (client_id={client_id}')

    @classmethod
    def remove(cls, client_id: int) -> None:
        """
        Delete the record for `client_id` from the database.

        Arguments
        ---------
        client_id: int
            The client_id for the record to delete.

        Example
        -------
        >>> from refitt.database.auth import Client
        >>> Client.remove(456)
        """
        execute(_REMOVE_CLIENT, client_id=client_id)
        log.debug(f'client credentials removed (client_id={client_id}')

    def embed(self) -> Dict[str, Any]:
        """Like `to_dict` but dissolved to simple types for export."""
        data = self.to_dict()
        data['client_key'] = self.client_key.value
        data['client_secret'] = self.client_secret.value
        data['client_created'] = str(self.client_created)
        return data
