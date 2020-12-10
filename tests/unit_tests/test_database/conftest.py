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

"""Fixtures for database tests."""


# type annotations
from typing import List, Dict, Any

# standard libs
import os
import json

# external libs
import pytest

# internal libs
from refitt import assets
from refitt.database.model import __VT


@pytest.fixture(scope='package')
def testdata() -> Dict[str, List[Dict[str, __VT]]]:
    """Load test data into in-memory dictionary."""

    def _format_name(path: str) -> str:
        return os.path.splitext(os.path.basename(path))[0]

    return {_format_name(path): json.loads(data)
            for path, data in assets.load_assets('database/test/*.json').items()}
