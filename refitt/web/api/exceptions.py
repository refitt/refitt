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

"""Exceptions specific to REFITT's API."""


class DataNotFound(Exception):
    """No data was provided in the request."""


class BadData(Exception):
    """The posted data was malformed or missing parameters."""


class AuthorizationNotFound(Exception):
    """Missing key:secret in authorization."""


class AuthorizationInvalid(Exception):
    """Secret did not match expected value."""


class PermissionDenied(Exception):
    """Action not permitted for current user/level."""
