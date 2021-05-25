# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core typing methods and annotation type definitions."""


# type annotations
from typing import TypeVar

# public interface
__all__ = ['coerce', ]


ValueType = TypeVar('ValueType', str, int, float, type(None))
def coerce(value: str) -> ValueType:
    """Automatically coerce string to typed value."""
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if value.lower() in ('null', 'none', ):
        return None
    elif value.lower() in ('true', ):
        return True
    elif value.lower() in ('false', ):
        return False
    else:
        return value
