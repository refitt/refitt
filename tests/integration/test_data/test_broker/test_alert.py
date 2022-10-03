# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Data broker alert integration tests."""


# external libs
from pytest import mark
from antares_client.search import get_by_id

# internal libs
from refitt.data.broker.antares import AntaresAlert
from refitt.database.model import Observation, Alert
from tests.unit.test_data.test_broker.test_alert import MockAlert


@mark.integration
class TestMockAlert:
    """Integrations for data broker client interface."""

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


@mark.integration
class TestAntaresService:
    """Test issues with Antares client library."""

    @mark.skip(reason='Invokes external API; only needed to test service')
    def test_alert_history(self) -> None:
        """Check specific antares locus/alerts."""
        locus = get_by_id('ANT2020ky6q')
        assert len(locus.alerts) == 1789
        alert = AntaresAlert.from_locus(locus)
        assert len(alert.previous) == 664  # alerts missing necessary properties

