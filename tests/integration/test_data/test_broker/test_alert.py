# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker alert integration tests."""


# external libs
import pytest
from antares_client.search import get_by_id

# internal libs
from refitt.data.broker.antares import AntaresAlert
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


class TestAntaresService:
    """Test issues with Antares client library."""

    @pytest.mark.skip(reason='Invokes external API; only needed to test service')
    def test_alert_history(self) -> None:
        """Check specific antares locus/alerts."""
        locus = get_by_id('ANT2020ky6q')
        assert len(locus.alerts) == 1789
        alert = AntaresAlert.from_locus(locus)
        assert len(alert.previous) == 664  # alerts missing necessary properties

