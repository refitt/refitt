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


"""Connect to one of the Antares streams."""

# type annotations
from __future__ import annotations
from functools import lru_cache
from typing import Dict, Iterator, Union

# standard libs
from datetime import datetime

# external libs
from antares_client import StreamingClient as _AntaresClient
from antares_client._api.models import Locus  # noqa: protected
from astropy.time import Time

# internal libs
from .client import ClientInterface
from .alert import AlertInterface
from ..database.observation import ObservationTypeNotFound


class AntaresAlert(AlertInterface):
    """An Antares Alert."""

    source_name = 'antares'

    @classmethod
    def from_locus(cls, locus: Locus) -> AntaresAlert:
        """Extract new pseudo-schema from existing `locus`."""
        data = {'locus_id': locus.locus_id,
                'ra': locus.ra,
                'dec': locus.dec,
                'properties': locus.properties,
                'alert_history': [{'alert_id': alert.alert_id,
                                   'mjd': alert.mjd,
                                   'ra': locus.ra,
                                   'dec': locus.dec,
                                   'properties': alert.properties}
                                  for alert in reversed(sorted(locus.alerts, key=(lambda alert: alert.mjd)))]}
        data['new_alert'] = data['alert_history'][0] # NOTE: sorting is most recent first
        return cls.from_dict(data)

    @property
    def object_name(self) -> str:
        return self.data['locus_id']

    @property
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {'antares': self.object_name,
                'ztf': self.data['properties']['ztf_object_id']}

    @property
    def object_type_name(self) -> str:
        return 'UNKNOWN'

    @property
    def object_ra(self) -> float:
        return float(self.data['ra'])

    @property
    def object_dec(self) -> float:
        return float(self.data['dec'])

    @property
    def object_redshift(self) -> float:
        return 99.99  # FIXME: not available?

    # ztf_fid property map
    obs_types: dict = {
        1: 'g-ztf',
        2: 'r-ztf'
    }

    @property
    @lru_cache(maxsize=None)
    def newest_alert_id(self) -> str:
        return self.data['properties']['newest_alert_id']

    @property
    @lru_cache(maxsize=None)
    def newest_alert(self) -> dict:
        # FIXME: this implementation reflects the old dictionary structure,
        #        we can have this just pull the first item from the list instead
        for alert_data in self.data['alert_history']:
            if alert_data['alert_id'] == self.newest_alert_id:
                return alert_data
        else:
            raise KeyError(f'{self.newest_alert_id} not found in alert history')

    @property
    @lru_cache(maxsize=None)
    def ztf_fid(self) -> int:
        return int(self.newest_alert['properties']['ztf_fid'])

    @property
    def observation_type_name(self) -> str:
        try:
            return self.obs_types[self.ztf_fid]
        except KeyError as error:
            raise ObservationTypeNotFound(f'{error} not in AntaresAlert.obs_types') from error

    @property
    def observation_value(self) -> float:
        return float(self.newest_alert['properties']['ztf_magpsf'])

    @property
    def observation_error(self) -> float:
        return float(self.newest_alert['properties']['ztf_sigmapsf'])

    @property
    def observation_time(self) -> datetime:
        mjd = self.data['properties']['newest_alert_observation_time']
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
        properties = alert['new_alert']['properties']
        return properties['ztf_distpsnr1'] > 2 and properties['ztf_ssdistnr'] == -999.0
