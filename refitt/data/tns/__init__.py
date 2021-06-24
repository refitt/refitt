# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) integrations."""


# type annotations
from __future__ import annotations
from typing import Dict, Any, Optional

# standard libs
import json
import logging
from dataclasses import dataclass
from functools import cached_property
from abc import ABC

# external libs
import requests
from cmdkit.config import Namespace, ConfigurationError

# internal libs
from ...core.config import config
from ...core.schema import DictSchema, SchemaError, ListSchema

# public interface
__all__ = ['TNS', 'TNSError', 'TNSConfig', 'TNSNameSearchResult', 'TNSObjectSearchResult', ]


# initialize module level logger
log = logging.getLogger(__name__)


@dataclass
class TNSConfig:
    """Auth Headers for TNS API queries."""

    key: str
    bot_id: int
    bot_name: str = 'REFITT_BOT'

    schema = DictSchema.of({
        'key': str,
        'bot_id': int,
        'bot_name': str
    })

    @classmethod
    def from_dict(cls, other: Dict[str, Any]) -> TNSConfig:
        """Build from existing dictionary."""
        return cls(**cls.schema.ensure(other))

    @classmethod
    def from_config(cls, cfg: Namespace = None) -> TNSConfig:
        """Load from default/given configuration."""
        try:
            return TNSConfig.from_dict(cfg or config.tns)
        except AttributeError as error:
            raise ConfigurationError(f'Missing \'tns\' section') from error
        except SchemaError as error:
            raise ConfigurationError(f'TNSConfig: {error}') from error

    @cached_property
    def headers(self) -> dict:
        """Headers for TNS requests."""
        return {'User-Agent': f'tns_marker{{"tns_id":{self.bot_id}, "type":"bot", "name":"{self.bot_name}"}}'}

    def format_data(self, **parameters) -> dict:
        """Build search data for request."""
        return {'api_key': self.key, 'data': json.dumps(parameters)}


TNS_URL_BASE = 'https://www.wis-tns.org/api'
TNS_URL_SEARCH = f'{TNS_URL_BASE}/get/search'
TNS_URL_OBJECT = f'{TNS_URL_BASE}/get/object'


class TNSError(Exception):
    """Exception raises from bad requests to TNS service."""


class TNS:
    """Query interface for Transient Name Server query service."""

    config: TNSConfig

    def __init__(self, cfg: Namespace = None) -> None:
        """Initialize TNSConfig with `cfg`."""
        self.config = TNSConfig.from_config(cfg)

    def search_name(self, ztf_id: str) -> TNSNameSearchResult:
        """Query TNS with internal `ztf_id`."""
        data = self.config.format_data(internal_name=ztf_id)
        response = requests.post(TNS_URL_SEARCH, data=data, headers=self.config.headers)
        if response.status_code == 200:
            return TNSNameSearchResult.from_response(response)
        else:
            data = response.json()
            raise TNSError(response.status_code, data['id_message'])

    def search_object(self, iau_name: str) -> TNSObjectSearchResult:
        """Query TNS with `iau_name` for object details."""
        data = self.config.format_data(objname=iau_name, photometry='1', spectra='1')
        response = requests.post(TNS_URL_OBJECT, data=data, headers=self.config.headers)
        if response.status_code == 200:
            return TNSObjectSearchResult.from_response(response)
        else:
            data = response.json()
            raise TNSError(response.status_code, data['id_message'])


@dataclass
class TNSQueryResult(ABC):
    """Abstract base class for TNS query results."""

    data: dict
    schema = DictSchema.any()

    @classmethod
    def from_dict(cls, other: dict) -> TNSQueryResult:
        """Build from existing dictionary."""
        return cls(data=cls.schema.ensure(other))

    @classmethod
    def from_response(cls, response: requests.Response) -> TNSQueryResult:
        """Build from existing `response`."""
        return cls.from_dict(response.json())


@dataclass
class TNSNameSearchResult(TNSQueryResult):
    """Query results from a name search."""

    data: dict
    schema = DictSchema.of({
        'id_code': int,
        'id_message': str,
        'data': DictSchema.of({
            'received_data': DictSchema.of({'internal_name': str, }),
            'reply': ListSchema.of(
                DictSchema.of({
                    'objname': str,
                    'prefix': str,
                    'objid': int
                 }), size=1)
        })
    })

    @property
    def object_name(self) -> str:
        """The TNS/IAU designation."""
        return self.data['data']['reply'][0]['objname']


@dataclass
class TNSObjectSearchResult(TNSQueryResult):
    """Query results from an object details search."""

    data: dict
    schema = DictSchema.of({
        'id_code': int,
        'id_message': str,
        'data': DictSchema.of({
            'received_data': DictSchema.of({
                'objname': str,
                'photometry': int,
                'spectra': int
            }),
            # NOTE: schema too complicated and variable to force adherence
            'reply': DictSchema.any()
        })
    })

    @property
    def type_name(self) -> Optional[str]:
        """Supernova classification name for object."""
        return self.data['data']['reply']['object_type']['name']

    @property
    def redshift(self) -> Optional[float]:
        """Redshift for object."""
        return self.data['data']['reply']['redshift']
