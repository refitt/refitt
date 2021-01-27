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

"""Implements the common `Client` interface for all broker clients."""


# type annotations
from __future__ import annotations

# standard libs
from abc import ABC, abstractmethod
from typing import Tuple, Iterator

# internal libs
from .alert import AlertInterface


class ClientInterface(ABC):
    """Table class for all stream clients."""

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
