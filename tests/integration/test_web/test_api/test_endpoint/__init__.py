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

"""Web API endpoint integration tests."""



# external libs
import pytest
import requests

# internal libs
from tests.integration.test_web import URL_BASE


class TestTokenEndpoint:
    """Test session token."""

    def test_token_not_found(self) -> None:
        """Requests without authorization bearer token are Forbidden."""
        response = requests.get(f'{URL_BASE}/info')
