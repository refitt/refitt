# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Convenient decorator for wrapping calls with profiler."""


# type annotations
from __future__ import annotations
from typing import Callable, Any

# standard libs
import pstats
import cProfile
import functools

# internal libs
from refitt.core.logging import Logger

# public interface
__all__ = ['profile', ]


log = Logger.with_name(__name__)


def profile(filename: str = None, sort_by: pstats.SortKey = pstats.SortKey.TIME) -> Callable:
    """Decorator that invokes `cProfile.Profile` as context manager."""

    def decorator(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapped(*args, **kwargs) -> Any:

            log.debug(f'Profiling {func}')
            with cProfile.Profile() as profiler:
                result = func(*args, **kwargs)

            stats = pstats.Stats(profiler)
            stats.sort_stats(sort_by)
            if filename is None:
                stats.print_stats()
            else:
                stats.dump_stats(filename=filename)
                log.debug(f'Profile data written to file ({filename})')

            return result

        return wrapped
    return decorator
