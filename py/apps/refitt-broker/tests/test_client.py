# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker client tests."""


# type annotations
from __future__ import annotations
from typing import Iterator

# external libs
from pytest import mark

# internal libs
from refitt.database.model import Object, Observation, Alert
from refitt.data.broker.client import ClientInterface
from tests.test_data.test_broker.test_alert import MockAlert


class MockClient(ClientInterface):
    """A test implementation of the ClientInterface."""

    is_connected: bool = False

    def connect(self) -> None:
        if self.is_connected:
            raise AttributeError('MockClient is already connected')
        else:
            self.is_connected = True

    def close(self) -> None:
        self.is_connected = False

    def __iter__(self) -> Iterator[MockAlert]:
        if self.is_connected:
            yield from iter(MockAlert.from_random, None)
        else:
            raise AttributeError('MockClient is not connected')

    @staticmethod
    def filter_above_equator(alert: MockAlert) -> bool:
        return alert.object_dec > 0

    @staticmethod
    def filter_has_provider_a(alert: MockAlert) -> bool:
        return 'sourceA' in alert.object_aliases


class TestClient:
    """Test basic interfaces for MockClient."""

    @mark.unit
    def test_init_with_credentials(self) -> None:
        client = MockClient(topic='topic', credentials=('key', 'secret'))
        assert client.topic == 'topic'
        assert client.credentials == ('key', 'secret')

    @mark.unit
    def test_error_on_not_connected(self) -> None:
        """Check that we are connected within context manager."""
        try:
            for alert in MockClient(topic='topic', credentials=('key', 'secret')):
                print(alert)
                break
        except Exception as error:
            assert isinstance(error, AttributeError)
            assert error.args == ('MockClient is not connected', )
        else:
            raise AssertionError('Expected AttributeError')

    @mark.unit
    def test_iterator(self) -> None:
        """Check alert yielded from iterator."""
        with MockClient(topic='topic', credentials=('key', 'secret')) as stream:
            for alert in stream:
                assert isinstance(alert, MockAlert)
                break

    @mark.integration
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
