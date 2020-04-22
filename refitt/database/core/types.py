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

"""Special types/classes for connecting to the database."""

# type annotations
from typing import NamedTuple


class ServerAddress(NamedTuple):
    """Combines a `host` and `port`."""
    host: str
    port: int


class UserAuth(NamedTuple):
    """A username and password pair."""
    username: str
    password: str = None

    def __str__(self) -> str:
        """String representation."""
        username = 'None' if self.username is None else f'"{self.username}"'
        password = 'None' if self.password is None else '"****"'
        return f'{self.__class__.__name__}(username={username}, password={password})'

    def __repr__(self) -> str:
        """Interactive representation."""
        username = 'None' if self.username is None else f'"{self.username}"'
        password = 'None' if self.password is None else '"****"'
        return f'{self.__class__.__name__}(username={username}, password={password})'
