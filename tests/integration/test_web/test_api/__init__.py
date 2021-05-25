# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for API."""


# standard libs
from contextlib import contextmanager

# internal libs
from refitt.web.token import Secret
from refitt.database.model import Client, Session


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


@contextmanager
def temp_revoke_access(client_id: int) -> None:
    """Temporarily revoke access (i.e., client.valid = false)."""
    previous = Client.from_id(client_id).valid
    try:
        Client.update(client_id, valid=False)
        yield
    finally:
        Client.update(client_id, valid=previous)


@contextmanager
def temp_expired_token(client_id: int) -> str:
    """Temporarily yield a token that is expired. Fix in database after."""
    client = Client.from_id(client_id)
    session = Session.from_client(client_id)
    try:
        yield Session.new(client.user_id, -86400).encrypt()
    finally:
        Session.update(session.id, token=session.token,
                       created=session.created, expires=session.expires)


@contextmanager
def restore_session(client_id: int) -> None:
    """Force restore token for session for given client."""
    client = Client.from_id(client_id)
    session = Session.from_client(client.id).to_dict()
    try:
        yield
    finally:
        Session.update(session['id'], token=session['token'], expires=session['expires'], created=session['created'])


@contextmanager
def restore_client(client_id: int) -> None:
    """Force restore token for session for given client."""
    client = Client.from_id(client_id).to_dict()
    try:
        yield
    finally:
        Client.update(client['id'], key=client['key'], secret=client['secret'], created=client['created'])
