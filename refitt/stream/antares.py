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

# standard libs
from typing import Tuple, List, Dict, Iterator, Any

# external libs
from antares_client import Client as _Antares_Client

# internal libs
from .client import ClientInterface
from .alert import AlertInterface


class AntaresAlert(AlertInterface):
    """An Antares Alert."""

    @property
    def alert_id(self) -> int:
        """The "alert_id" specified in the "new_alert" data."""
        return int(self.data['new_alert']['alert_id'])


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