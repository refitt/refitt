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
    >>> from refitt.web import requests
    >>> requests.get('recommendation')
    {...}

Note:
    A `login` method issues the initial necessary GET /token request.
    That token is held in-memory and all future requests use it.
    To force a new GET /token request, use `login(force=True)`.
    This is attempted on your behalf if the response suggests the
    token was expired.
"""

# type annotations
from typing import Dict, Any, Callable

# standard libs
import os
import urllib
import functools
from datetime import datetime

# external libs
import requests

# internal libs
from ..core.logging import Logger
from ..core.config import config, ConfigurationError
from ..database.auth import Claim, Token


class APIError(Exception):
    """A failed request."""

    def __str__(self) -> str:
        status, *messages = self.args
        return f'[{status}] ' + ' - '.join(messages)

    def __repr__(self) -> str:
        return str(self)


# module level logger
log = Logger(__name__)


# global access token held in-memory
TOKEN: Token = None


def login(force: bool = False) -> Dict[str, Claim]:
    """
    Request new access token and add to configuration file.
    """

    global TOKEN
    if 'api' not in config.keys():
        raise ConfigurationError('[api] section missing')
    if TOKEN is None:
        existing_token = config['api'].get('access_token', None)
        if existing_token is not None:
            TOKEN = Token(existing_token)
    if not force and TOKEN is not None:
        return TOKEN

    site = config['api'].get('site', 'http://localhost:5000')
    path = urllib.request.urljoin(site, 'token')
    key, secret = config['api']['client_key'], config['api']['client_secret']
    response = requests.get(path, auth=(key, secret))
    response_data = response.json()
    if response.status_code != 200:
        raise APIError(response.status_code, response_data['message'])

    data = response_data['response']['token']
    TOKEN = Token(data['access_token'])
    log.debug('GET /token')
    return data


def authenticated(func: Callable) -> Callable:
    """Ensure valid access token."""

    @functools.wraps(func)
    def method(*args, **kwargs) -> Dict[str, Any]:

        global TOKEN
        if not TOKEN:
            login()
        try:
            return func(*args, **kwargs)
        except APIError as error:
            status, message = error.args
            if status == 401 and 'unauthorized: token expired' in message:
                login(force=True)
                return func(*args, **kwargs)
            else:
                raise

    return method


@authenticated
def request(action: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """
    Issue a request to the REFITT API.

    Arguments
    ---------
    action: str
        The action verb for the request (get, put, ...).
    endpoint: str
        The path for the API (e.g., '/profile/user/1').
    **kwargs:
        All keyword arguments are forwarded to `requests.<action>`.
    """
    site = config['api'].get('site', 'http://localhost:5000')
    path = urllib.request.urljoin(site, endpoint)
    method = getattr(requests, action)
    response = method(path, data=kwargs.pop('data', None), json=kwargs.pop('json', None),
                      headers={'Authorization': f'Bearer {TOKEN.value}'}, params=kwargs)
    response_data = response.json()
    if response.status_code != 200:
        raise APIError(response.status_code, response_data['message'])
    return response_data['response']


# exposed methods
get = functools.partial(request, 'get')
put = functools.partial(request, 'put')
post = functools.partial(request, 'post')
delete = functools.partial(request, 'delete')