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

"""
Assets/templates required by REFITT.
"""

# standard libs
import os


def load(filename: str) -> str:
    """Load an asset by its base `filename`."""
    dirname = os.path.dirname(__file__)
    filepath = os.path.join(dirname, filename)
    with open(filepath, mode='r') as source:
        return source.read()
