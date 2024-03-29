# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for database model tests."""


# type annotations
from typing import List, Dict

# standard libs
import os
import json

# external libs
from pytest import fixture

# internal libs
from refitt import assets
from refitt.database.model import __VT


Record = Dict[str, __VT]
TestData = Dict[str, List[Record]]


@fixture(scope='package')
def testdata() -> TestData:
    """Load test data as in-memory dictionary."""

    def _format_name(path: str) -> str:
        return os.path.splitext(os.path.basename(path))[0]

    return {_format_name(path): json.loads(data)
            for path, data in assets.load_assets('database/test/*.json').items()}
