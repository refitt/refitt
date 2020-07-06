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
from typing import Tuple, List, Dict, Iterator, Any, Union

# standard libs
from datetime import datetime

# external libs
from antares_client import Client as _Antares_Client

# internal libs
from .client import ClientInterface
from .alert import AlertInterface


class AntaresAlert(AlertInterface):
    """An Antares Alert."""

    source_name = 'antares'

    @property
    def object_name(self) -> str:
        return f'ANT{self.data["new_alert"]["locus_id"]}'

    @property
    def object_aliases(self) -> Dict[str, Union[int, str]]:
        return {'antares': self.object_name,
                'ztf': self.data['new_alert']['properties']['ztf_object_id']}

    @property
    def object_type_name(self) -> str:
        return 'UNKNOWN'

    @property
    def object_ra(self) -> float:
        return float(self.data['new_alert']['ra'])

    @property
    def object_dec(self) -> float:
        return float(self.data['new_alert']['dec'])

    @property
    def object_redshift(self) -> float:
        return 99.99  # FIXME: not available?

    @property
    def observation_type_name(self) -> str:
        # FIXME: why is this not consistent?!
        passband = self.data['new_alert']['properties']['passband'].lower()
        return f'{passband}-ztf'

    @property
    def observation_value(self) -> float:
        return float(self.data['new_alert']['properties']['ztf_psfmag'])

    @property
    def observation_error(self) -> float:
        return float(self.data['new_alert']['properties']['ztf_sigpsfmag'])

    @property
    def observation_time(self) -> datetime:
        return datetime.fromtimestamp(self.data['timestamp_unix'])

class AntaresClient(ClientInterface):
    """Client connection to Antares."""

    # client code already defined via `antares_client.Client`
    _client: _Antares_Client = None

    def connect(self) -> None:
        """Connect to Antares."""
        key, token = self.credentials
        self._client = _Antares_Client([self.topic], api_key=key, api_secret=token)

    def close(self) -> None:
        """Close connection to Antares."""
        self._client.close()

    def __iter__(self) -> Iterator[AntaresAlert]:
        """Iterate over alerts."""
        for _, alert in self._client.iter():
            yield AntaresAlert.from_dict(alert)

    @staticmethod
    def filter_not_extragalactic_sso(alert: AntaresAlert) -> bool:
        """
        Rejects all "ztf_distpsnr1 > 2 & ztf_ssdistnr = -999.0".
        Approximates possible SN candidates.
        """
        properties = alert['new_alert']['properties']
        return properties['ztf_distpsnr1'] > 2 and properties['ztf_ssdistnr'] == -999.0
