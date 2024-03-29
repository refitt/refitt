# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Define AntaresAlert and AntaresClient."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Iterator, Union, Optional

# standard libs
from datetime import datetime

# external libs
from antares_client import StreamingClient as _AntaresClient
from antares_client.models import Locus
from astropy.time import Time

# internal libs
from refitt.data.broker.client import ClientInterface
from refitt.data.broker.alert import AlertInterface, AlertError
from refitt.core.logging import Logger

# public interface
__all__ = ['AntaresAlert', 'AntaresClient', ]

# module logger
log = Logger.with_name(__name__)


class AntaresAlert(AlertInterface):
    """An Antares Alert."""

    source_name = 'antares'
    previous: List[AntaresAlert] = []

    @classmethod
    def from_locus(cls, locus: Locus) -> AntaresAlert:
        """Extract new pseudo-schema from existing `locus`."""

        base = {'locus_id': locus.locus_id,
                'ra': locus.ra,
                'dec': locus.dec,
                'properties': locus.properties,
                'catalogs': locus.catalogs}

        # NOTE: we pre-filter prior history to check that we have necessary properties
        #       e.g., missing `ztf_magpsf` indicates an upper/lower limit event (so we throw it out)
        previous = [{'alert_id': alert.alert_id, 'mjd': alert.mjd,
                     'ra': locus.ra, 'dec': locus.dec,
                     'properties': alert.properties}
                    for alert in reversed(sorted(locus.alerts, key=(lambda alert: alert.mjd)))
                    if cls.__has_needed_properties(alert.properties)]

        if not previous:
            raise AlertError(f'Missing necessary properties on all alerts ({locus.locus_id})')
        elif len(previous) < len(locus.alerts):
            missing = len(locus.alerts) - len(previous)
            log.info(f'{missing} alert(s) not included because of missing properties ({locus.locus_id})')

        alert = cls.from_dict({**base, 'new_alert': previous[0]})
        if len(previous) > 1:
            alert.previous = [cls.from_dict({**base, 'new_alert': alert}) for alert in previous[1:]]
        else:
            alert.previous = []
        return alert

    __needed_properties: List[str] = [
        'ztf_fid',
        'ztf_magpsf',
        'ztf_sigmapsf',
    ]

    @classmethod
    def __has_needed_properties(cls, properties: dict) -> bool:
        """True if all fields found in alert `properties`."""
        for name in cls.__needed_properties:
            if name not in properties:
                return False
        else:
            return True

    @property
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {'antares': self.data['locus_id'],
                'ztf': self.data['properties']['ztf_object_id'],
                'ztf_candid': int(self.data['new_alert']['properties']['ztf_candid'])}

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
        return None  # Note:  not available from Antares -- will be updated later by TNS

    # ztf_fid property map
    obs_types: dict = {
        1: 'g-ztf',
        2: 'r-ztf',
        3: 'i-ztf',
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

    # Note: antares-client package already provides a good interface
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
            try:
                yield AntaresAlert.from_locus(locus)
            except AlertError as error:
                log.error(str(error))

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
            log.error(f'Missing necessary data for filter=not_extragalactic_sso')
            return False

    @staticmethod
    def filter_neargaia(alert: AntaresAlert) -> bool:
        """Rejects all `ztf_neargaia <= 2` (arc seconds)."""
        try:
            return alert['new_alert']['properties']['ztf_neargaia'] > 2
        except KeyError as exc:
            log.error(f'Missing necessary data for filter=neargaia ({exc})')
            return False
