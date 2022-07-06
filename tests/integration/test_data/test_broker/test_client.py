# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker client integration tests."""


# external libs
from pytest import mark

# internal libs
from refitt.database.model import ObjectType, Object, ObservationType, Observation, Alert
from tests.unit.test_data.test_broker.test_client import MockClient


@mark.integration
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
