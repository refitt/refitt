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
REFITT based web requests.

This module is a thin wrapper around the popular `requests` package.
Only relative-paths need be specified and the token-based authentication
is handled automatically.

Example:
    >>> from refitt.web import request
    >>> request.get('recommendation')
    {...}
"""

# type annotations
from typing import Tuple, Dict, Any, Callable, Optional, Type, TypeVar

# standard libs
import re
from contextlib import contextmanager
import logging
import functools
import webbrowser
from urllib.request import urljoin  # noqa: missing stub for urllib

# external libs
import requests as __requests

# internal libs
from ..core.config import config, update_config
from .token import Key, Secret, Token
from .api.response import STATUS


# initialize module level logger
log = logging.getLogger(__name__)


class APIError(Exception):
    """A failed request."""

    def __str__(self) -> str:
        status, *messages = self.args
        return f'[{status}] ' + ' - '.join(messages)

    def __repr__(self) -> str:
        return str(self)


def __join_path(site: str, port: Optional[int], path: str) -> str:
    return urljoin(site if not port else f'{site}:{port}', path)


__has_protocol: re.Pattern = re.compile(r'^http(s)?://')
def __join_site(path: str) -> str:
    site = config.api.site
    site = f'http://{site}' if __has_protocol.match(site) is None else site
    return __join_path(site, config.api.port, path)


__CT = TypeVar('__CT', Key, Secret, Token)
def __get(var: Type[__CT]) -> Optional[__CT]:
    found = config.api.get(var.__name__.lower(), None)
    return None if not found else var(found)


# global reference to credentials
KEY: Optional[Key] = None
SECRET: Optional[Secret] = None
TOKEN: Optional[Token] = None


def login(force: bool = False) -> Tuple[Key, Secret]:
    """
    Get client key and secret.

    If not already stored in the configuration file, navigate to the web interface and get
    the credentials and update the configuration file.

    Using `force` will force new credential creation.
    """

    global KEY
    global SECRET
    if KEY and SECRET and not force:
        return KEY, SECRET

    KEY = __get(Key)
    SECRET = __get(Secret)
    if KEY and SECRET and not force:
        return KEY, SECRET

    if not webbrowser.open(config.api.login):
        print(f'Navigate to {config.api.login} and paste your client key and secret here ...')

    KEY = Key(input('Client key: '))
    SECRET = Secret(input('Client secret: '))
    update_config('user', {'api': {'key': KEY.value, 'secret': SECRET.value}})
    return KEY, SECRET


# global setting to require tokens get persisted
PERSIST_TOKEN: bool = False


def refresh_token(force: bool = False, persist: bool = False) -> Token:
    """Request new access token with existing key and secret."""

    global TOKEN
    TOKEN = __get(Token)
    if TOKEN and not force:
        return TOKEN

    url = __join_site('token')
    key, secret = login()
    response = __requests.get(url, auth=(key.value, secret.value))
    response_data = response.json()
    if response.status_code != STATUS['OK']:
        raise APIError(response.status_code, response_data['Message'])

    TOKEN = Token(response_data['Response']['token'])
    if persist or PERSIST_TOKEN:
        update_config('user', {'api': {'token': TOKEN.value}})
    return TOKEN


def authenticated(func: Callable) -> Callable:
    """Ensure valid access token."""

    @functools.wraps(func)
    def method(*args, **kwargs) -> Dict[str, Any]:
        global TOKEN
        if not TOKEN:
            refresh_token()
        try:
            return func(*args, **kwargs)
        except APIError as error:
            status, message = error.args
            if status == STATUS['Forbidden'] and message == 'Token expired':
                refresh_token(force=True)
                return func(*args, **kwargs)
            else:
                raise

    return method


def format_request(endpoint: str) -> str:
    """Build URL for request."""
    return __join_site(endpoint.lstrip('/'))


@authenticated
def request(action: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """
    Issue a request to the REFITT API.

    Args:
        action (str):
            The action verb for the request (get, put, ...).
        endpoint (str):
            The path for the API (e.g., '/user/1').
        **kwargs:
            All keyword arguments are forwarded to the method (i.e., `action`).
    """
    url = __join_site(endpoint.lstrip('/'))
    method = getattr(__requests, action)
    response = method(url, data=kwargs.pop('data', None), json=kwargs.pop('json', None),
                      headers={'Authorization': f'Bearer {TOKEN.value}'},
                      cert=kwargs.pop('cert', None), verify=kwargs.pop('verify', None),
                      params=kwargs)
    response_data = response.json()
    if response.status_code != STATUS['OK']:
        raise APIError(response.status_code, response_data['Message'])
    return response_data['Response']


# exposed methods
get = functools.partial(request, 'get')
put = functools.partial(request, 'put')
post = functools.partial(request, 'post')
delete = functools.partial(request, 'delete')


@contextmanager
def use_auth(key: str, secret: str) -> None:
    """Temporarily set `request.KEY` and `request.SECRET` in context manager."""
    global KEY, SECRET
    old_key, old_secret = KEY, SECRET
    try:
        KEY, SECRET = Key(key), Secret(secret)
        yield
    finally:
        KEY, SECRET = old_key, old_secret


@contextmanager
def use_token(token: str) -> None:
    """Temporarily set `request.TOKEN` in context manager."""
    global TOKEN
    old_token = TOKEN
    try:
        TOKEN = Token(token)
        yield
    finally:
        TOKEN = old_token
