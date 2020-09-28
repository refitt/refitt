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

"""REFITT's API /object end-point implementation."""


# internal libs
from ....database.observation import Object, ObjectType


def get_types() -> list:
    """Return list of all object types."""
    return [record.embed() for record in ObjectType.select()]


def get_type(name: str) -> dict:
    return ObjectType.from_id_or_name(name).embed()


def get(name: str) -> dict:
    return Object.from_id_or_name(name).embed()

