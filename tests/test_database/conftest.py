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


Records = List[Dict[str, Any]]
@pytest.fixture(scope='package')
def testdata() -> Dict[str, Records]:
    """Load test data into in-memory dictionary."""
    data = assets.load_assets('database/test/*.json')
    return {os.path.basename(path)[:-5]: json.loads(content)
            for path, content in data.items()}
