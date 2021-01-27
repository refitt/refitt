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

"""Unit tests for data broker alert interface."""


# type annotations
from __future__ import annotations
from typing import Iterator

# internal libs
from refitt.data.broker.client import ClientInterface
from tests.unit.test_data.test_broker.test_alert import MockAlert


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


class TestMockClient:
    """Test basic interfaces for MockClient."""

    def test_init_with_credentials(self) -> None:
        client = MockClient(topic='topic', credentials=('key', 'secret'))
        assert client.topic == 'topic'
        assert client.credentials == ('key', 'secret')

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

    def test_iterator(self) -> None:
        """Check alert yielded from iterator."""
        with MockClient(topic='topic', credentials=('key', 'secret')) as stream:
            for alert in stream:
                assert isinstance(alert, MockAlert)
                break
