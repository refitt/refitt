# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Base64 encoding/decoding for representing raw data streams."""


# standard libs
from base64 import encodebytes as _encode, decodebytes as _decode

# public interface
__all__ = ['encode', 'decode', ]


def decode(data: str) -> bytes:
    """Decode base64 encoded string `data` back to raw bytes."""
    return _decode(data.encode())


def encode(data: bytes) -> str:
    """Encode raw bytes into base64 encode string."""
    return _encode(data).decode().strip()
