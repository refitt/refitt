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
from typing import Tuple, Dict, Any, Union, Callable, Optional, Type, TypeVar

# standard libs
import re
import logging
import functools
import webbrowser
from urllib.request import urljoin  # noqa: missing stub for urllib
from contextlib import contextmanager

# external libs
import requests as __requests

# internal libs
from ..core.config import config, update_config
from .token import Key, Secret, Token
from .api.response import STATUS


# type defs
Request = __requests.Request
Response = __requests.Response


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
    if response.status_code != STATUS['OK']:
        raise APIError(response)
    response_data = response.json()
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
            response, = error.args
            response_status = response.status_code
            response_message = response.json().get('Response').get('Message')
            if response_status == STATUS['Forbidden'] and response_message == 'Token expired':
                refresh_token(force=True)
                return func(*args, **kwargs)
            else:
                raise

    return method


def format_request(endpoint: str) -> str:
    """Build URL for request."""
    return __join_site(endpoint.lstrip('/'))


# find information from headers
FILENAME_PATTERN: re.Pattern = re.compile(r'^attachment; filename=(.*)$')


def get_json(response: Response) -> dict:
    """Return parsed JSON content of the `response`."""
    return response.json()


def get_file(response: Response) -> dict:
    """Return parsed file attachment of the `response`."""
    data = response.content
    info = response.headers.get('Content-Disposition', '')
    name, = FILENAME_PATTERN.match(info).groups()
    return {name: data}


CONTENT_TYPE: Dict[str, Callable[[Response], Union[bytes, dict]]] = {
    'application/json': get_json,
    'application/octet-stream': get_file,
}


def get_content(response_type: str, response: Response) -> Union[bytes, dict]:
    return CONTENT_TYPE[response_type](response)


def get_protocol(response: Response) -> str:
    """Parse version info"""
    protocol, path = response.request.url.split('://')
    return protocol.upper()


def get_protocol_version(response: Response) -> str:
    """Get semantic version for HTTP."""
    return '.'.join(list(str(response.raw.version)))


@authenticated
def request(action: str, endpoint: str,
            raise_on_error: bool = True, extract_response: bool = True,
            **kwargs) -> dict:
    """
    Issue authenticated request to the REFITT API.

    Args:
        action (str):
            The action verb for the request (get, put, ...).
        endpoint (str):
            The path for the API (e.g., '/user/1').
        raise_on_error (bool):
            Raise APIError if status is not 200. (default: True)
        extract_response (bool):
            If a JSON response is given and the 'Response' section is found
            and we have a 200 response, extract it directly as the return value.
        **kwargs:
            All keyword arguments are forwarded to the method (i.e., `action`).

    Returns:
        response_data (dict):
            If not `extract_response`, this will be a dictionary with 'status' (int),
            'headers' (dict), and 'content' (either bytes or dict).
            If `extract_response`, the 'Response' section will be directly returned.
    """
    url = __join_site(endpoint.lstrip('/'))
    method = getattr(__requests, action)
    response = method(url,
                      data=kwargs.pop('data', None), json=kwargs.pop('json', None), files=kwargs.pop('files', None),
                      headers={'Authorization': f'Bearer {TOKEN.value}'}, cert=kwargs.pop('cert', None),
                      verify=kwargs.pop('verify', None), params=kwargs)
    response_data = get_content(response.headers['Content-Type'], response)
    if response.status_code != STATUS['OK'] and raise_on_error:
        raise APIError(response)
    if isinstance(response_data, dict) and extract_response:
        return response_data['Response']  # NOTE: allow KeyError if 'Response' is missing
    else:
        return {
            'status': response.status_code,
            'headers': {'Protocol': get_protocol(response),
                        'Version': get_protocol_version(response),
                        **response.headers},
            'content': response_data
        }


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
