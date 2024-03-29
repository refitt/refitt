# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Tests for Refitt's web token mechanics."""


# type annotations
from __future__ import annotations

# standard libs
import re
import random
import string
from datetime import datetime, timedelta

# external libs
import pytest
from hypothesis import given, strategies as st
from cmdkit.config import Configuration, Namespace, ConfigurationError

# internal libs
from refitt.web.token import Cipher, CryptoDigits, RootKey, Key, Secret, Token, JWT


FAKE_ROOTKEY = Cipher.new_rootkey()
CONFIG = Configuration(fake=Namespace({'api': {'rootkey': FAKE_ROOTKEY.value}}))


class MockCipher(Cipher):
    """A Cipher with hard-coded configuration."""

    @staticmethod
    def load_rootkey(__config: Configuration) -> RootKey:
        """Always returns fixed rootkey for testing."""
        return Cipher.load_rootkey(CONFIG)


@pytest.mark.unit
class TestCipher:
    """Unit tests for Cipher."""

    def test_init(self) -> None:
        """Create a Cipher directly with an existing rootkey."""
        assert isinstance(Cipher(FAKE_ROOTKEY), Cipher)  # RootKey
        assert isinstance(Cipher(FAKE_ROOTKEY.encode()), Cipher)  # bytes
        assert isinstance(Cipher(FAKE_ROOTKEY.value), Cipher)  # str

    def test_from_config(self) -> None:
        """Cipher can pull rootkey from configuration."""
        assert MockCipher.from_config()._key == FAKE_ROOTKEY

    def test_from_config_missing(self) -> None:
        """Cipher expects 'api.rootkey' in configuration."""
        with pytest.raises(ConfigurationError):
            Cipher.load_rootkey(Configuration())

    def test_new_rootkey(self) -> None:
        """Can create new rootkey."""
        assert isinstance(Cipher.new_rootkey(), RootKey)

    @given(size=st.integers(min_value=1, max_value=1024))
    def test_encode_decode(self, size: int) -> None:
        """Test round-trip encode decode."""
        data = self.random_data(size)
        cipher = MockCipher.from_config()
        encrypted_data = cipher.encrypt(data)
        assert isinstance(data, bytes)
        assert isinstance(encrypted_data, bytes)
        assert data != encrypted_data
        assert len(data) < len(encrypted_data)
        assert data == cipher.decrypt(encrypted_data)

    @staticmethod
    def random_data(size: int) -> bytes:
        """Generate random bytes with `size`."""
        return CryptoDigits.generate(size).value.encode()


class CryptoDigitsCommonTests:
    """Generic test suite for all implementations."""

    size = None
    impl = CryptoDigits
    pattern = re.compile(r'^[a-zA-Z0-9-_=]+$')

    def test_initialization(self) -> None:
        """Direct initialize with digits."""
        value = self.random_digits()
        digits = self.impl(value)
        assert isinstance(digits, self.impl)
        assert digits.value == value

    def test_generate(self) -> None:
        """Should be able to generate new digits automatically."""
        digits = self.impl.generate()
        assert isinstance(digits, self.impl)

    def test_has_length(self) -> None:
        """Digits should report their own length."""
        digits = self.impl(self.random_digits())
        assert len(digits) == self.size

    def test_hashing(self) -> None:
        """Digits should be hashable (returning a hashed representation)."""
        digits = self.impl(self.random_digits())
        hashed = digits.hashed()
        assert isinstance(hashed, self.impl)
        assert hashed.value != digits.value

    STR = re.compile(r'^[a-zA-Z0-9-_=]{1,3}\.\.\.[a-zA-Z0-9-_=]{1,3}$')

    def test_string(self) -> None:
        """String representation only shows starting and ending digits."""
        digits = self.impl(self.random_digits())
        assert self.STR.match(str(digits))

    def test_representation(self) -> None:
        """Representation includes hash/non-hash."""
        digits = self.impl(self.random_digits())
        digits_hashed = digits.hashed()
        assert repr(digits) == f'<{self.impl.__name__}(\'{digits}\')>'
        assert repr(digits_hashed) == f'<{self.impl.__name__}[hashed](\'{digits_hashed}\')>'

    def test_equal(self) -> None:
        """Digits can check if they are the same to an other."""
        digits = self.impl(self.random_digits())
        assert digits == self.impl(digits.value)

    def test_equal_against_hashing(self) -> None:
        """Hashed versions of digits are report as equal to un-hashed."""
        digits = self.impl(self.random_digits())
        assert digits.hashed() == self.impl(digits.value)

    def test_encode(self) -> None:
        """Can encode digits as raw bytes."""
        digits = self.impl(self.random_digits())
        assert digits.encode() == digits.value.encode('utf-8')

    def test_encrypt(self) -> None:
        """Can encrypt/decrypt with Cipher."""
        digits = self.impl(self.random_digits())
        cipher = MockCipher.from_config()
        encrypted_digits = digits.encrypt(cipher)
        assert isinstance(encrypted_digits, bytes)
        assert self.impl.decrypt(encrypted_digits, cipher) == digits

    def random_digits(self, size: int = None) -> str:
        """Generate a string of randomly selected ASCII digits."""
        size = size or self.size or random.randint(1, 1024)
        return ''.join(random.choices(string.ascii_letters, k=size))


@pytest.mark.unit
class TestRootKey(CryptoDigitsCommonTests):
    """Unit tests for RootKey."""

    size = RootKey._size
    impl = RootKey


@pytest.mark.unit
class TestKey(CryptoDigitsCommonTests):
    """Unit tests for Key."""

    size = Key._size
    impl = Key


@pytest.mark.unit
class TestSecret(CryptoDigitsCommonTests):
    """Unit tests for Secret."""

    size = Secret._size
    impl = Secret


@pytest.mark.unit
class TestToken(CryptoDigitsCommonTests):
    """Unit tests for Token."""

    size = Token._size  # NOTE: should be None
    impl = Token

    @given(st.integers(min_value=1, max_value=1024))
    def test_initialization(self, size: int) -> None:
        digits = self.impl(''.join(random.choices(string.ascii_letters, k=size)))
        assert isinstance(digits, self.impl)

    @given(st.integers(min_value=1, max_value=1024))
    def test_has_length(self, size: int) -> None:
        """Token should report its own length."""
        digits = self.impl(self.random_digits(size))
        assert len(digits) == size

    @given(st.integers(min_value=1, max_value=1024))
    def test_generate(self, size: int) -> None:
        """Should be able to generate new digits automatically."""
        digits = self.impl.generate(size)
        assert isinstance(digits, self.impl)
        assert len(digits) == size


@pytest.mark.unit
class TestJWT:
    """Tests for JSON-Web Token implementation."""

    def test_attributes(self) -> None:
        """Test attribute access."""
        sub, exp = 1, datetime.utcnow()
        jwt = JWT(sub=sub, exp=exp)
        assert isinstance(jwt, JWT)
        assert jwt.sub == sub
        assert jwt.exp == exp

    def test_init_with_none(self) -> None:
        """Create JWT with `exp` as None."""
        jwt = JWT(sub=1, exp=None)
        assert isinstance(jwt, JWT)
        assert jwt.exp is None

    def test_init_with_datetime(self) -> None:
        """Create JWT with `exp` as datetime."""
        now = datetime.utcnow()
        jwt = JWT(sub=1, exp=now)
        assert isinstance(jwt, JWT)
        assert isinstance(jwt.exp, datetime)
        assert jwt.exp == now

    def test_init_with_timedelta(self) -> None:
        """Create JWT with `exp` as timedelta."""
        delta = timedelta(minutes=15)
        jwt = JWT(sub=1, exp=delta)
        assert isinstance(jwt, JWT)
        assert isinstance(jwt.exp, datetime)
        assert jwt.exp < datetime.utcnow() + delta

    def test_init_with_unix_timestamp(self) -> None:
        """Create JWT with `exp` as unix timestamp (float)."""
        timestamp = float(datetime.utcnow().timestamp())
        jwt = JWT(sub=1, exp=timestamp)
        assert isinstance(jwt, JWT)

    def test_init_with_unix_timestamp_integer(self) -> None:
        """Create JWT with `exp` as unix timestamp (int -- nearest second)."""
        timestamp = int(datetime.utcnow().timestamp())
        jwt = JWT(sub=1, exp=timestamp)
        assert isinstance(jwt, JWT)

    def test_repr(self) -> None:
        """Representation shows attributes."""
        exp = datetime.utcnow()
        assert repr(JWT(sub=1, exp=None)) == 'JWT(sub=1, exp=None)'
        assert repr(JWT(sub=1, exp=exp)) == f'JWT(sub=1, exp={repr(exp)})'

    def test_to_from_dict(self) -> None:
        """JWT can be initialized from an existing dictionary and exported to one."""
        claims = {'sub': 1, 'exp': datetime.utcnow()}
        assert isinstance(JWT.from_dict(claims), JWT)
        assert JWT.from_dict(claims).to_dict() == claims

    def test_encode(self) -> None:
        """JWT can be encoded as a raw JSON string."""
        assert JWT(sub=1, exp=1624167581).encode() == b'{"sub": 1, "exp": 1624167581}'
        assert JWT(sub=1, exp=None).encode() == b'{"sub": 1, "exp": -1}'

    def test_encrypt(self) -> None:
        """JWT can be encrypted and decrypted with a Cipher."""
        jwt = JWT(sub=1, exp=1624167581)
        jwt_encrypted = jwt.encrypt(MockCipher.from_config())
        assert isinstance(jwt_encrypted, str)

    def test_decrypt(self) -> None:
        """JWT can be decrypted from bytes with a Cipher."""
        jwt = JWT(sub=1, exp=1624167581)
        cipher = MockCipher.from_config()
        jwt_encrypted = jwt.encrypt(cipher)
        jwt_new = JWT.decrypt(jwt_encrypted, cipher)
        assert isinstance(jwt_new, JWT)
        assert jwt.to_dict() == jwt_new.to_dict()

