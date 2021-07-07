# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

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
