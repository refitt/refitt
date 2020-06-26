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

"""Logging for HTTP requests."""

# type annotations
from typing import Callable

# standard libs
from functools import wraps

# external libs
from flask import request

# internal libs
from ...core.logging import Logger


log = Logger(__name__)


def logged(route: Callable[..., dict]) -> Callable[..., dict]:
    """Log the request."""

    @wraps(route)
    def logged_(*args, **kwargs) -> dict:
        log.info(f'{request.method} {request.path}')
        return route(*args, **kwargs)

    return logged_
