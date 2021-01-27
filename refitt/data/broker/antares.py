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

"""Define AntaresAlert and AntaresClient"""


# type annotations
from __future__ import annotations
from typing import List, Dict, Iterator, Union, Optional

# standard libs
import logging
from datetime import datetime
from functools import cached_property

# external libs
from antares_client import StreamingClient as _AntaresClient
from antares_client._api.models import Locus  # noqa: protected
from astropy.time import Time

# internal libs
from .client import ClientInterface
from .alert import AlertInterface


# initialize module level logger
log = logging.getLogger(__name__)


class AntaresAlert(AlertInterface):
    """An Antares Alert."""

    source_name = 'antares'
    previous: List[AntaresAlert] = []

    _needed_properties: List[str] = [
        'ztf_fid',
        'ztf_magpsf',
        'ztf_sigmapsf',
    ]

    @classmethod
    def from_locus(cls, locus: Locus) -> AntaresAlert:
        """Extract new pseudo-schema from existing `locus`."""

        def has_needed_props(data: dict) -> bool:
            for name in cls._needed_properties:
                if name not in data:
                    return False
            else:
                return True

        base = {'locus_id': locus.locus_id,
                'ra': locus.ra,
                'dec': locus.dec,
                'properties': locus.properties}

        # NOTE: we pre-filter prior history to check that we have necessary properties
        #       e.g., missing `ztf_magpsf` indicates a upper/lower limit event (so we throw it out)
        previous = [{'alert_id': alert.alert_id, 'mjd': alert.mjd,
                     'ra': locus.ra, 'dec': locus.dec,
                     'properties': alert.properties}
                    for alert in reversed(sorted(locus.alerts, key=(lambda alert: alert.mjd)))
                    if has_needed_props(alert.properties)]

        if not previous:
            raise ValueError('Missing necessary properties in all alerts')

        self = cls.from_dict({**base, 'new_alert': previous[0]})
        if len(previous) > 1:
            self.previous = [cls.from_dict({**base, 'new_alert': alert}) for alert in previous[1:]]
        else:
            self.previous = []
        return self

    @property
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {'antares': self.data['locus_id'],
                'ztf': self.data['properties']['ztf_object_id']}

    @property
    def id(self) -> str:
        return self.object_aliases['antares']

    @property
    def object_type_name(self) -> str:
        return 'Unknown'

    @property
    def object_ra(self) -> float:
        return float(self.data['ra'])

    @property
    def object_dec(self) -> float:
        return float(self.data['dec'])

    @property
    def object_redshift(self) -> Optional[float]:
        return None  # FIXME: not available?

    # ztf_fid property map
    obs_types: dict = {
        1: 'g-ztf',
        2: 'r-ztf'
    }

    @property
    def ztf_fid(self) -> int:
        return int(self.data['new_alert']['properties']['ztf_fid'])

    @property
    def observation_type_name(self) -> str:
        try:
            return self.obs_types[self.ztf_fid]
        except KeyError as error:
            raise KeyError(f'Missing \'{error}\' in AntaresAlert.obs_types') from error

    @property
    def observation_value(self) -> float:
        return float(self.data['new_alert']['properties']['ztf_magpsf'])

    @property
    def observation_error(self) -> float:
        return float(self.data['new_alert']['properties']['ztf_sigmapsf'])

    @property
    def observation_time(self) -> datetime:
        mjd = self.data['new_alert']['mjd']
        return Time(mjd, format='mjd', scale='utc').datetime


class AntaresClient(ClientInterface):
    """Client connection to Antares."""

    # client code already defined via `antares_client.Client`
    _client: _AntaresClient = None

    def connect(self) -> None:
        """Connect to Antares."""
        key, secret = self.credentials
        self._client = _AntaresClient([self.topic], api_key=key, api_secret=secret)

    def close(self) -> None:
        """Close connection to Antares."""
        self._client.close()

    def __iter__(self) -> Iterator[AntaresAlert]:
        """Iterate over alerts."""
        for topic, locus in self._client.iter():
            yield AntaresAlert.from_locus(locus)

    @staticmethod
    def filter_not_extragalactic_sso(alert: AntaresAlert) -> bool:
        """
        Rejects all "ztf_distpsnr1 > 2 & ztf_ssdistnr = -999.0".
        Approximates possible SN candidates.
        """
        try:
            properties = alert['new_alert']['properties']
            return properties['ztf_distpsnr1'] > 2 and properties['ztf_ssdistnr'] == -999.0
        except KeyError:
            log.warning(f'Missing necessary data for filter=not_extragalactic_sso')
            return False

