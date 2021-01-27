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

"""Data broker client integration tests."""


# internal libs
from refitt.database.model import ObjectType, Object, ObservationType, Observation, Alert
from tests.unit.test_data.test_broker.test_alert import MockAlert
from tests.unit.test_data.test_broker.test_client import MockClient


class TestMockClient:
    """Integrations for data broker client interface."""

    def test_stream_to_database(self) -> None:
        """Stream alerts from client to database."""
        with MockClient(topic='topic', credentials=('key', 'secret')) as stream:
            for count, alert in enumerate(stream):
                received = alert.to_database()
                assert Alert.from_id(received.id) == received
                assert received.observation.id == received.observation_id
                if count > 100:
                    break
