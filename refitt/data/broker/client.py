# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Implements the common `Client` interface for all broker clients."""


# type annotations
from __future__ import annotations

# standard libs
from abc import ABC, abstractmethod
from typing import Tuple, Iterator

# internal libs
from .alert import AlertInterface

# public interface
__all__ = ['ClientInterface', ]


class ClientInterface(ABC):
    """Generic interface for all stream client implementations."""

    topic: str = None
    credentials: Tuple[str, str] = None

    def __init__(self, topic: str, credentials: Tuple[str, str]) -> None:
        """Initialize topics and connection configuration."""
        self.topic = topic
        self.credentials = credentials

    @abstractmethod
    def connect(self) -> None:
        """Must define connection logic."""

    @abstractmethod
    def close(self) -> None:
        """Must define close logic."""

    @abstractmethod
    def __iter__(self) -> Iterator[AlertInterface]:
        """Should yield back Alert objects."""

    def __enter__(self) -> ClientInterface:
        """Context manager setup."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Context manager shutdown."""
        self.close()

    # clients can define static methods that start with the `filter_`
    # prefix which can be used to reject incoming alerts.

    @staticmethod
    def filter_none(alert: AlertInterface) -> bool:  # noqa: unused
        """Accept all incoming alerts."""
        return True
