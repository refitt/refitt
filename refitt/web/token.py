# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Cryptographic data and JSON Web Tokens (JWT)."""


# type annotations
from __future__ import annotations
from typing import Dict, TypeVar, Optional, Union

# standard libs
import re
import json
import string
import random
import hashlib
import logging
import functools
from datetime import datetime, timedelta

# external libs
from cryptography.fernet import Fernet, InvalidToken
from cmdkit.config import Configuration, ConfigurationError

# internal libs
from ..core.config import config

# public interface
__all__ = ['AuthError', 'TokenNotFound', 'TokenInvalid', 'TokenExpired', 'Cipher',
           'CryptoDigits', 'RootKey', 'Key', 'Secret', 'Token', 'JWT', ]


# initialize module level logger
log = logging.getLogger(__name__)


class AuthError(Exception):
    """Generic Authentication/authorization errors."""


class TokenNotFound(AuthError):
    """The access token was not found."""


# NOTE: piggy back on cryptography
class TokenInvalid(AuthError):
    """The token is not legitimate."""


class TokenExpired(AuthError):
    """The token is past it's expiration datetime."""


class Cipher:
    """
    A Fernet cipher.

    Example:
        >>> rootkey = Cipher.new_rootkey()
        >>> cipher = Cipher(rootkey)
        >>> cipher
        <Cipher(key=<RootKey('M2F...BZ3')>)>
    """

    _fernet: Fernet
    _key: RootKey

    def __init__(self, key: Union[str, bytes, RootKey]) -> None:
        """Initialize cipher with given root `key`."""
        self._key = RootKey(key)
        self._fernet = Fernet(self._key.encode())

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt `data` with the Cipher."""
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        """Decrypt `data` with the Cipher."""
        return self._fernet.decrypt(data)

    @classmethod
    @functools.lru_cache(maxsize=None)
    def from_config(cls) -> Cipher:
        """Load the root key from the configuration."""
        return cls(cls.load_rootkey(config))

    @staticmethod
    def load_rootkey(__config: Configuration) -> RootKey:
        """Load rootkey from configuration."""
        try:
            return RootKey(__config.api.rootkey)
        except AttributeError as error:
            raise ConfigurationError('Missing \'api.rootkey\'') from error

    @staticmethod
    def new_rootkey() -> RootKey:
        """Generate a new cryptography 'rootkey' for deployments."""
        return RootKey(Fernet.generate_key().decode())

    def __repr__(self) -> str:
        """Representation shows RootKey."""
        return f'<{self.__class__.__name__}(key={repr(self._key)})>'


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

    def __init__(self, value: Union[str, bytes, CryptoDigits]) -> None:
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
        self.value = value if isinstance(value, str) else value.decode()

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
        """Direct view of the hexdigits."""
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
        return self.__class__(self)

    @classmethod
    def generate(cls, size: int = None) -> CryptoDigits:
        """Generate a new instance of `size`."""
        _size = size if size is not None else cls._size
        if _size is not None:
            digits = (random.SystemRandom().choice(cls._digits) for _ in range(_size))
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
        """Return encoded bytes."""
        return self.value.encode('utf-8')

    def encrypt(self, cipher: Cipher = None) -> bytes:
        """Encrypt digits using a Cipher."""
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


class RootKey(CryptoDigits):
    """A 44-digit key."""
    _size = 44


class Key(CryptoDigits):
    """A 16-digit key."""
    _size = 16


class Secret(CryptoDigits):
    """A 64-digit secret."""
    _size = 64  # sha256 gives the same number of digits


class Token(CryptoDigits):
    """A variable-length token."""
    _size = None  # depends on JWT data

    def __len__(self) -> int:
        return len(self._value)


# value types for JWT claims
Claim = TypeVar('Claim', int, str)
ExpTime = TypeVar('ExpTime', datetime, timedelta, float, int, type(None))


class JWT:
    """A JSON Web Token."""

    _sub: int
    _exp: Optional[datetime]

    def __init__(self, sub: int, exp: ExpTime) -> None:
        """Initialize directly with `sub` and `exp` claims."""
        self.sub = sub
        self.exp = exp

    @property
    def sub(self) -> int:
        """Get subject claim (client.id)."""
        return self._sub

    @sub.setter
    def sub(self, value: int) -> None:
        """Set subject claim (client.id)."""
        self._sub = int(value)

    @property
    def exp(self) -> Optional[datetime]:
        """Get expiration claim (Unix time)."""
        return self._exp

    @exp.setter
    def exp(self, value: ExpTime) -> None:
        """Set expiration claim (Unix time)."""
        if value is None or isinstance(value, datetime):
            self._exp = value
        elif isinstance(value, timedelta):
            self._exp = datetime.now() + value
        elif isinstance(value, (int, float)):
            self._exp = None if value == -1 else datetime.fromtimestamp(float(value))
        else:
            raise TypeError(f'JWT.exp: unsupported type {type(value)}')

    def __str__(self) -> str:
        """String representation."""
        return f'JWT(sub={repr(self.sub)}, exp={repr(self.exp)})'

    def __repr__(self) -> str:
        """Interactive representation (see also: __str__)."""
        return str(self)

    def to_dict(self) -> Dict[str, Union[int, None, datetime]]:
        """Convert to standard dictionary."""
        return dict(sub=self.sub, exp=self.exp)

    @classmethod
    def from_dict(cls, other: Dict[str, Union[int, datetime]]) -> JWT:
        """Initialize from existing dictionary."""
        return cls(**other)

    def encode(self) -> bytes:
        """JSON-serialize the JWT to bytes."""
        payload = self.to_dict()
        payload['exp'] = -1 if self.exp is None else int(self.exp.timestamp())
        return json.dumps(payload).encode('utf-8')

    @classmethod
    def decode(cls, data: Union[str, bytes]) -> JWT:
        """Deserialize JSON `data` using a Cipher."""
        return cls.from_dict(json.loads(data if isinstance(data, str) else data.decode()))

    def encrypt(self, cipher: Cipher = None) -> str:
        """Encrypt an encoded version of the JWT using a Cipher."""
        _cipher = cipher if cipher is not None else Cipher.from_config()
        return _cipher.encrypt(self.encode()).decode('utf-8')

    @classmethod
    def decrypt(cls, token: Union[str, bytes], cipher: Cipher = None) -> JWT:
        """Decrypt a `token` as a new JWT."""
        _token = None
        try:
            _token = token if isinstance(token, bytes) else str(token).encode()
            _cipher = cipher if cipher is not None else Cipher.from_config()
            return cls.decode(_cipher.decrypt(_token))
        except InvalidToken as error:
            raise TokenInvalid(f'Token invalid: \'{Token(_token.decode())}\'') from error
