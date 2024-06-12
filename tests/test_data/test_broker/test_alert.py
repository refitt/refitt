# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker alert integration tests."""


# type annotations
from __future__ import annotations
from typing import List, Dict, Optional, Union, Callable

# standard libs
import os
import json
import string
import random
from uuid import uuid4 as gen_uuid
from functools import cached_property
from datetime import datetime, timedelta

# external libs
from pytest import mark, raises
from names_generator import generate_name
from antares_client.search import get_by_id

# internal libs
from refitt.assets import load_asset
from refitt.data.broker.alert import AlertInterface
from refitt.data.broker.antares import AntaresAlert
from refitt.database.model import Observation, Alert


fields: List[str] = [
    'source_name',
    'object_aliases',
    'object_type_name',
    'object_ra',
    'object_dec',
    'object_redshift',
    'observation_type_name',
    'observation_value',
    'observation_error',
    'observation_time',
]


def _generate_random_object_aliases() -> Dict[str, str]:
    return {provider: generate_name(style='underscore')
            for provider in random.choices(string.ascii_lowercase, k=random.randint(1, 4))}


def _generate_random_object_ra() -> float:
    return random.uniform(0, 180)


def _generate_random_object_dec() -> float:
    return random.uniform(-90, 90)


def _generate_random_object_redshift() -> Optional[float]:
    return None if random.random() < 0.1 else random.uniform(0, 1)


def _generate_random_object_type_name() -> str:
    object_type_data = load_asset('database/core/object_type.json')
    object_types = json.loads(object_type_data)
    object_type = random.choice(object_types)
    return object_type['name']


def _generate_random_observation_type_name() -> str:
    observation_type_data = load_asset('database/core/observation_type.json')
    observation_types = json.loads(observation_type_data)
    observation_type = random.choice(observation_types)
    return observation_type['name']


def _generate_random_observation_value() -> float:
    return random.uniform(16, 22)


def _generate_random_observation_error() -> float:
    return random.uniform(0.1, 1)


def _generate_random_observation_time() -> str:
    return (datetime.now() - random.uniform(0, 60) * timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')


__VT = Union[str, float, datetime, None]
_generator_map: Dict[str, Callable[..., __VT]] = {
    'source_name': (lambda: 'test_broker'),  # NOTE: defined in test data assets for database
    'object_aliases': _generate_random_object_aliases,
    'object_type_name': _generate_random_object_type_name,
    'object_ra': _generate_random_object_ra,
    'object_dec': _generate_random_object_dec,
    'object_redshift': _generate_random_object_redshift,
    'observation_type_name': _generate_random_observation_type_name,
    'observation_value': _generate_random_observation_value,
    'observation_error': _generate_random_observation_error,
    'observation_time': _generate_random_observation_time,
}


def _random_choice(typename: str) -> __VT:
    try:
        return _generator_map[typename]()
    except KeyError:
        raise KeyError(f'No generator with name \'{typename}\'')


class MockAlert(AlertInterface):
    """Simple, low level implementation of an Alert for testing purposes."""

    @cached_property
    def id(self) -> str:
        return str(gen_uuid())

    @property
    def source_name(self) -> str:
        return self.data['source_name']

    @property
    def object_aliases(self) -> Dict[str, str]:
        return self.data['object_aliases']

    @property
    def object_type_name(self) -> str:
        return self.data['object_type_name']

    @property
    def object_ra(self) -> float:
        return self.data['object_ra']

    @property
    def object_dec(self) -> float:
        return self.data['object_dec']

    @property
    def object_redshift(self) -> float:
        return self.data['object_redshift']

    @property
    def observation_type_name(self) -> str:
        return self.data['observation_type_name']

    @property
    def observation_value(self) -> float:
        return self.data['observation_value']

    @property
    def observation_error(self) -> float:
        return self.data['observation_error']

    @property
    def observation_time(self) -> datetime:
        return datetime.strptime(self.data['observation_time'], '%Y-%m-%d %H:%M:%S')

    @classmethod
    def from_random(cls) -> MockAlert:
        """Create a new MockAlert with random data."""
        return MockAlert({field: _random_choice(field) for field in _generator_map})


class TestAlert:
    """Test MockAlert for basic behavior."""

    @mark.unit
    def test_error_on_empty_init(self) -> None:
        """The constructor requires a single argument."""
        with raises(TypeError):
            MockAlert()  # noqa

    @mark.unit
    def test_error_on_named_parameters(self) -> None:
        """The constructor does not support named parameters."""
        with raises(TypeError):
            MockAlert({}, other=False, thing=2)  # noqa

    @mark.unit
    def test_data_initialization(self) -> None:
        """The data passed in is assigned to `data`."""
        data = {'name': 'my_object', 'value': 3.14}
        alert = MockAlert(data)
        assert alert.data is data

    @mark.unit
    def test_data_error_if_not_dict(self) -> None:
        """The data must be a dict or TypeError is raised."""
        for data in [(1, 2, 3), {1, 2, 3, }, 'a, b, c', 3.14]:
            with raises(TypeError):
                MockAlert(data)  # noqa

    @mark.unit
    def test_type_coercion(self) -> None:
        """The data passed in is assigned to `data`."""
        data = {'name': 'my_object', 'value': 3.14}
        alert = MockAlert(data)
        other = MockAlert(alert)
        assert alert.data == other.data

    @mark.unit
    def test_equality(self) -> None:
        for _ in range(10):
            alert = MockAlert.from_random()
            assert alert == MockAlert(alert)
            assert alert != MockAlert.from_random()

    @mark.unit
    def test_from_local(self, tmpdir: str) -> None:
        """Test that we can load from a local file."""
        data = MockAlert.from_random().data
        path = f'{tmpdir}/data/broker/mock_alert_00.json'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode='w') as localfile:
            json.dump(data, localfile, indent=4)
        assert MockAlert.from_local(path).data == data

    @mark.unit
    def test_to_local(self, tmpdir: str) -> None:
        """Test that we can dump to a local file."""
        path = f'{tmpdir}/data/broker/mock_alert_01.json'
        os.makedirs(os.path.dirname(path), exist_ok=True)
        alert = MockAlert.from_random()
        alert.to_local(path)
        assert MockAlert.from_local(path) == alert

    @mark.integration
    def test_backfill(self) -> None:
        """Create alert with prior history and test backfill."""

        # Prepare mock alerts
        alert = MockAlert.from_random()
        alert.previous = [MockAlert.from_random() for _ in range(10)]
        for a in alert.previous:
            a.data = {**a.data,
                      'source_name': alert.source_name,
                      'object_aliases': alert.object_aliases,
                      'object_type_name': alert.object_type_name, }

        alert.previous = sorted(alert.previous, key=(lambda _a: _a.observation_time))

        # Full backfill adds alert and all previous
        obs_count = Observation.count()
        alert_count = Alert.count()

        records = alert.backfill_database()
        assert Observation.count() == obs_count + len(alert.previous) + 1
        assert Alert.count() == alert_count + len(alert.previous) + 1

        # If you delete the last two then only those will be filled back in
        obs_count = Observation.count()
        alert_count = Alert.count()

        for a in records[-2:]:
            Alert.delete(a.id)
            Observation.delete(a.observation_id)

        del records[-2]
        del records[-1]

        assert Observation.count() == obs_count - 2
        assert Alert.count() == alert_count - 2

        obs_count = Observation.count()
        alert_count = Alert.count()

        records.extend(alert.backfill_database())
        assert Observation.count() == obs_count + 2
        assert Alert.count() == alert_count + 2

        # Clean up all added records
        for a in records:
            Alert.delete(a.id)
            Observation.delete(a.observation_id)

        a = alert._record
        Alert.delete(a.id)
        Observation.delete(a.observation_id)


class TestAntaresService:
    """Test issues with Antares client library."""

    @mark.skip(reason='Invokes external API; only needed to test service')
    @mark.integration
    def test_alert_history(self) -> None:
        """Check specific antares locus/alerts."""
        locus = get_by_id('ANT2020ky6q')
        assert len(locus.alerts) == 1789
        alert = AntaresAlert.from_locus(locus)
        assert len(alert.previous) == 664  # alerts missing necessary properties
