# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Database model integration tests."""


# standard libs
import json


def json_roundtrip(data: dict) -> dict:
    """Input `data` is returned after JSON dump/load round trip."""
    return json.loads(json.dumps(data))
