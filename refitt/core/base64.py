# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""Base64 encoding/decoding for representing raw data streams."""


# standard library
from base64 import encodebytes as _encode, decodebytes as _decode

# public interface
__all__ = ['encode', 'decode', ]


def decode(data: str) -> bytes:
    """Decode base64 encoded string `data` back to raw bytes."""
    return _decode(data.encode())


def encode(data: bytes) -> str:
    """Encode raw bytes into base64 encode string."""
    return _encode(data).decode().strip()
