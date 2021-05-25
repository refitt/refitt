# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker alert integration tests."""


# internal libs
from refitt.database.model import Observation, Alert
from tests.unit.test_data.test_broker.test_alert import MockAlert


class TestMockAlert:
    """Integrations for data broker client interface."""

    def test_backfill(self) -> None:
        """Create alert with prior history and test backfill."""

        alert = MockAlert.from_random()
        alert.previous = [MockAlert.from_random() for _ in range(10)]
        for a in alert.previous:
            a.data = {**a.data,
                      'source_name': alert.source_name,
                      'object_aliases': alert.object_aliases,
                      'object_type_name': alert.object_type_name, }

        alert.previous = sorted(alert.previous, key=(lambda _a: _a.observation_time))

        obs_count = Observation.count()
        alert_count = Alert.count()

        records = alert.backfill_database()
        assert Observation.count() == obs_count + len(alert.previous) + 1
        assert Alert.count() == alert_count + len(alert.previous) + 1

        obs_count = Observation.count()
        alert_count = Alert.count()

        for a in records[-2:]:
            Alert.delete(a.id)
            Observation.delete(a.observation_id)

        assert Observation.count() == obs_count - 2
        assert Alert.count() == alert_count - 2

        obs_count = Observation.count()
        alert_count = Alert.count()

        alert.backfill_database()
        assert Observation.count() == obs_count + 2
        assert Alert.count() == alert_count + 2
