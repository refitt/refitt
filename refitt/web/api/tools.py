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
from typing import Any, Callable, List, Dict, TypeVar

# standard libs
import json

# external libs
from flask import Request

# internal libs
from .response import PayloadNotFound, PayloadMalformed, PayloadInvalid, ParameterNotFound, ParameterInvalid
from ...core import typing


JSONData = Dict[str, Any]
DataContent = TypeVar('DataContent', bytes, JSONData)


def parse_json(data: bytes) -> JSONData:
    """Decode and parse JSON `data`."""
    try:
        return json.loads(data.decode())
    except json.JSONDecodeError as error:
        raise PayloadMalformed('Invalid JSON data') from error


data_formats: Dict[str, Callable[[bytes], DataContent]] = {
    'json': parse_json,
}


def require_data(request: Request, data_format: str = 'json',
                 validate: Callable[[DataContent], Any] = None) -> DataContent:
    """Check for data and parse appropriately, optionally pass to `validate` callback."""

    payload = request.data
    if not payload:
        raise PayloadNotFound('Missing data in request')

    parser = data_formats[data_format]
    data = parser(payload)

    if validate:
        try:
            validate(data)
        except Exception as error:
            raise PayloadInvalid(f'Payload content invalid: ({error})') from error

    return data


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
