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

"""Integration tests for API."""


# standard libs
from contextlib import contextmanager

# internal libs
from refitt.web.token import Secret
from refitt.database.model import Client


@contextmanager
def temp_secret(client_id: int) -> Secret:
    """Generate a new secret for testing, but re-insert old secret hash."""
    old = Client.from_id(client_id)
    old_secret, user_id = old.secret, old.user_id
    try:
        key, secret = Client.new_secret(user_id)
        yield secret
    finally:
        Client.update(client_id, secret=old_secret)
