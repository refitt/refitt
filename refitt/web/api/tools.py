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

"""Helper methods for dealing with API requests."""


# type annotations
from typing import Any, Callable, List, Dict, Union, Tuple

# standard libs
import os
import json

# external libs
from flask import Request

# internal libs
from .response import (PayloadNotFound, PayloadMalformed, PayloadInvalid, PayloadTooLarge,
                       ParameterNotFound, ParameterInvalid)
from ...core import typing


# type defs
ContentType = Union[bytes, dict]


def parse_none(data: bytes) -> bytes:
    """Return `data` as is."""
    return data


def parse_json(data: bytes) -> dict:
    """Decode and parse JSON `data`."""
    try:
        return json.loads(data.decode())
    except json.JSONDecodeError as error:
        raise PayloadMalformed('Invalid JSON data') from error


data_formats: Dict[str, Callable[[bytes], ContentType]] = {
    'json': parse_json,
    'bytes': parse_none,
}


def require_data(request: Request, data_format: str = 'json', required_fields: List[str] = None,
                 validate: Callable[[ContentType], Any] = None) -> ContentType:
    """Check for data and parse appropriately, optionally pass to `validate` callback."""

    payload = request.data
    if not payload:
        raise PayloadNotFound('Missing data in request')

    parser = data_formats[data_format]
    data = parser(payload)

    if required_fields is not None:
        if data_format != 'json':
            raise NotImplementedError(f'Cannot check fields for non-JSON data formats')
        for field in required_fields:
            if field not in data:
                raise PayloadMalformed(f'Missing required field \'{field}\'')
        for field in data:
            if field not in required_fields:
                raise PayloadMalformed(f'Unexpected field \'{field}\'')

    if validate:
        try:
            validate(data)
        except Exception as error:
            raise PayloadInvalid(f'Payload content invalid: ({error})') from error

    return data


def require_file(request: Request, allowed_extensions: List[str] = None, size_limit: int = None) -> Tuple[str, bytes]:
    """Inspect `request` for files and return file type and contents."""
    if len(request.files) < 1:
        raise PayloadMalformed('No file attached to request')
    if len(request.files) > 1:
        raise PayloadMalformed('More than one file attached to request')
    (name, stream), = request.files.items()
    if not name:
        raise PayloadMalformed('Missing name for file attachment')
    if '.' not in name:
        raise PayloadMalformed('Missing file extension for name')
    file_basename, file_type = os.path.splitext(os.path.basename(name))
    file_type = file_type.strip('.')
    if allowed_extensions is not None:
        # FIXME: better support for compound types (e.g., '.fits.gz')
        for extension in allowed_extensions:
            if name.endswith('.' + extension.strip('.')):
                file_type = extension
                break
        else:
            raise PayloadMalformed(f'File type \'{file_type}\' not supported')
    data = stream.read()
    if size_limit is not None and len(data) > size_limit:
        raise PayloadTooLarge(f'File exceeds maximum size of {size_limit} bytes')
    return file_type, data


def coerce_types(args: Dict[str, str]) -> Dict[str, typing.ValueType]:
    """Coerce values automatically."""
    return {field: typing.coerce(value) for field, value in args.items()}


def collect_parameters(request: Request, required: List[str] = None, optional: List[str] = None,
                       defaults: Dict[str, Any] = None, allow_any: bool = False) -> Dict[str, Any]:
    """
    Collect parameters from `request` and coerce into appropriate types.
    Validate required parameters are provided
    """
    provided = dict(request.args)
    required = required or []
    optional = optional or []
    defaults = defaults or {}
    for field in required:
        if field not in provided:
            raise ParameterNotFound(f'Missing expected parameter: {field}')
    for field in provided:
        if field not in required and field not in optional and not allow_any:
            raise ParameterInvalid(f'Unexpected parameter: {field}')
    params = {**defaults, **coerce_types(provided)}
    for field, value in defaults.items():
        if not isinstance(params[field], type(value)):
            raise ParameterInvalid(f'Expected type \'{value.__class__.__name__}\' for parameter \'{field}\'')
    return params


def disallow_parameters(request: Request) -> None:
    """Consume `request.args` and raise if any present."""
    collect_parameters(request)
