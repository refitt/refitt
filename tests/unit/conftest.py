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

"""Fixtures for unit tests."""


# standard libs
import os
from datetime import datetime

# external libs
import pytest


@pytest.fixture(scope='package')
def tmpdir() -> str:
    """Ensure a new temporary directory exists and return its path."""
    date = datetime.now().strftime('%Y%m%d-%H%M%S')
    path = f'/tmp/refitt/tests/{date}'
    os.makedirs(path, exist_ok=True)
    return path
