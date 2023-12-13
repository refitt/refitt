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
        num_iter = 10  # No need to do this a million times
        num_observations = Observation.count()
        num_objects = Object.count()
        num_alerts = Alert.count()
        records = []
        with MockClient(topic='topic', credentials=('key', 'secret')) as stream:
            for alert in stream:
                received = alert.to_database()
                assert Alert.from_id(received.id) == received
                assert received.observation.id == received.observation_id
                records.append((received.id,
                                received.observation_id,
                                Observation.from_id(received.observation_id).object_id))
                if len(records) == num_iter:
                    break
        assert Observation.count() == num_observations + num_iter
        assert Object.count() == num_objects + num_iter
        assert Alert.count() == num_alerts + num_iter
        for alert_id, observation_id, object_id in records:
            Alert.delete(alert_id)
            Observation.delete(observation_id)
            Object.delete(object_id)
        assert Observation.count() == num_observations
        assert Object.count() == num_objects
        assert Alert.count() == num_alerts
