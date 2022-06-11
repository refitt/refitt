# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Transient Name Server (TNS) query interface."""


# type annotations
from __future__ import annotations
from typing import Dict, Any, Optional, Union, Type, Tuple

# standard libs
import json
from dataclasses import dataclass
from functools import cached_property
from abc import ABC, abstractclassmethod

# external libs
import requests
from cmdkit.config import ConfigurationError

# internal libs
from refitt.core.config import config
from refitt.core.logging import Logger
from refitt.core.schema import DictSchema, SchemaError, ListSchema

# public interface
__all__ = ['TNSInterface', 'TNSError', 'TNSConfig', 'TNSNameSearchResult', 'TNSObjectSearchResult',
           'TNSQueryCatalogResult', ]

# module logger
log = Logger.with_name(__name__)


@dataclass
class TNSConfig:
    """Auth Headers for TNS API queries."""

    key: str
    bot_id: int
    bot_name: str

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
    def from_config(cls, cfg: dict = None) -> TNSConfig:
        """Load from default/given configuration."""
        try:
            return TNSConfig.from_dict(cfg or config.tns)
        except AttributeError as error:
            raise ConfigurationError(f'Missing \'tns\' section') from error
        except SchemaError as error:
            raise ConfigurationError(str(error)) from error

    @cached_property
    def headers(self) -> dict:
        """Headers for TNS requests."""
        return {'User-Agent': f'tns_marker{{"tns_id":{self.bot_id}, "type":"bot", "name":"{self.bot_name}"}}'}

    def format_data(self, **parameters) -> dict:
        """Build search data for request."""
        if parameters:
            return {'api_key': self.key, 'data': json.dumps(parameters)}
        else:
            return {'api_key': self.key, }


TNS_URL_BASE = 'https://www.wis-tns.org'
TNS_URL_SEARCH = f'{TNS_URL_BASE}/api/get/search'
TNS_URL_OBJECT = f'{TNS_URL_BASE}/api/get/object'
TNS_URL_CATALOG = f'{TNS_URL_BASE}/system/files/tns_public_objects/tns_public_objects.csv.zip'


class TNSError(Exception):
    """Exception raises from bad requests to TNS service."""


class TNSInterface:
    """Query interface for Transient Name Server."""

    config: TNSConfig

    def __init__(self, cfg: Union[dict, TNSConfig] = None) -> None:
        """Initialize TNSConfig with `cfg`."""
        self.config = cfg if isinstance(cfg, TNSConfig) else TNSConfig.from_config(cfg)

    @cached_property
    def endpoint_map(self) -> Dict[str, Tuple[str, Type[TNSQueryResult]]]:
        """Map of endpoint label with request URL and result interface."""
        return {
            'name': (TNS_URL_SEARCH, TNSNameSearchResult),
            'object': (TNS_URL_OBJECT, TNSObjectSearchResult),
            'catalog': (TNS_URL_CATALOG, TNSQueryCatalogResult),
        }

    def query(self, endpoint: str, **parameters) -> requests.Response:
        """Issue request to TNS endpoint `url` with `data` and `headers`."""
        data = self.config.format_data(**parameters)
        url, response_type = self.endpoint_map[endpoint]
        response = requests.post(url, data=data, headers=self.config.headers)
        if response.status_code == 200:
            return response
        else:
            raise TNSError(response.status_code, endpoint)

    def search_name(self, ztf_id: str) -> TNSNameSearchResult:
        """Query TNS with internal `ztf_id`."""
        return TNSNameSearchResult.from_response(self.query('name', internal_name=ztf_id))

    def search_object(self, iau_name: str) -> TNSObjectSearchResult:
        """Query TNS with `iau_name` for object details."""
        return TNSObjectSearchResult.from_response(self.query('object', objname=iau_name))

    def search_catalog(self) -> TNSQueryCatalogResult:
        """Query TNS for full data catalog."""
        return TNSQueryCatalogResult.from_response(self.query('catalog'))


@dataclass
class TNSQueryResult(ABC):
    """Abstract base class for TNS query results."""

    _data: Union[bytes, dict]

    @abstractclassmethod
    def from_response(cls, response: requests.Response) -> TNSQueryResult:
        """Load results from request response.."""


@dataclass
class TNSQueryJSONResult(TNSQueryResult):
    """Abstract base class for TNS query results."""

    _schema = DictSchema.any()

    @classmethod
    def from_response(cls, response: requests.Response) -> TNSQueryJSONResult:
        """Build from request response."""
        return cls.from_dict(response.json())

    @classmethod
    def from_dict(cls, other: dict) -> TNSQueryJSONResult:
        """Build from existing dictionary."""
        return cls(cls._schema.ensure(other))


@dataclass
class TNSNameSearchResult(TNSQueryJSONResult):
    """Query results from a name search."""

    _data: dict
    _schema = DictSchema.of({
        'id_code': int,
        'id_message': str,
        'data': DictSchema.of({
            'received_data': DictSchema.of({'internal_name': str, }),
            'reply': ListSchema.of(
                DictSchema.of({
                    'objname': str,
                    'prefix': str,
                    'objid': int
                 }))
        })
    })

    @property
    def data(self) -> dict:
        """Reply body of the response payload."""
        return {} if not self._data['data']['reply'] else self._data['data']['reply'][0]

    @property
    def objname(self) -> Optional[str]:
        """The TNS/IAU designation."""
        return self.data.get('objname')

    @property
    def prefix(self) -> Optional[str]:
        """The TNS/IAU designation."""
        return self.data.get('prefix')

    @property
    def objid(self) -> Optional[int]:
        """The TNS/IAU designation."""
        return self.data.get('objid')


@dataclass
class TNSObjectSearchResult(TNSQueryJSONResult):
    """Query results from an object details search."""

    _data: dict
    _schema = DictSchema.of({
        'id_code': int,
        'id_message': str,
        'data': DictSchema.of({
            'received_data': DictSchema.of({'objname': str, }),
            'reply': DictSchema.any()  # NOTE: schema too complicated and variable to force adherence
        })
    })

    @property
    def data(self) -> dict:
        """Reply body of the response payload."""
        return self._data['data']['reply']

    @cached_property
    def is_empty(self) -> bool:
        """Check payload for data."""
        for field, content in self.data.items():
            if isinstance(content, dict):
                for field_code, field_data in content.items():
                    if isinstance(field_data, dict) and field_data.get('message', None) == 'No results found.':
                        return True
        else:
            return False

    @property
    def object_type_name(self) -> Optional[str]:
        """Supernova classification name for object."""
        return self.data['object_type']['name']

    @property
    def redshift(self) -> Optional[float]:
        """Redshift for object."""
        return self.data['redshift']


@dataclass
class TNSQueryCatalogResult(TNSQueryResult):
    """Response from TNS with CSV catalog data."""

    _data: bytes

    @classmethod
    def from_response(cls, response: requests.Response) -> TNSQueryCatalogResult:
        """Build from request response."""
        return cls(response.content)

    @property
    def data(self) -> bytes:
        """Access raw data content from query."""
        return self._data
