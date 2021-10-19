# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for forecast interface."""


# type annotations

# standard libs

# external libs
import pytest

# internal libs
from refitt.data.forecast import Forecast
from refitt.database.model import Observation as ObservationModel, Model
from tests.unit.test_forecast import generate_random_forecast


class TestForecastPublish:
    """Tests for database integration with forecast interface."""

    def test_publish(self) -> None:
        """Verify roundtrip with database."""
        data = generate_random_forecast()
        num_forecasts = Model.count()
        num_observations = ObservationModel.count()
        model = Forecast.from_dict(data).publish()
        assert Model.count() == num_forecasts + 1
        assert ObservationModel.count() == num_observations + 1
        assert model.to_dict() == Model.from_id(model.id).to_dict()
        Model.delete(model.id)
        ObservationModel.delete(model.observation_id)
        assert Model.count() == num_forecasts
        assert ObservationModel.count() == num_observations
        with pytest.raises(Model.NotFound):
            Model.from_id(model.id)
        with pytest.raises(ObservationModel.NotFound):
            ObservationModel.from_id(model.observation_id)

