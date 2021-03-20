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

"""Integration tests for forecast interface."""


# type annotations
from typing import Dict, Any

# standard libs
import io
import json
import string
import random

# external libs
import pytest
import numpy as np
from astropy.time import Time

# internal libs
from refitt.forecast import Forecast
from refitt.database.model import Observation as ObservationModel, Forecast as ForecastModel
from tests.unit.test_forecast import generate_random_forecast


class TestForecastPublish:
    """Tests for database integration with forecast interface."""

    def test_publish(self) -> None:
        """Verify roundtrip with database."""
        data = generate_random_forecast()
        num_forecasts = ForecastModel.count()
        num_observations = ObservationModel.count()
        model = Forecast.from_dict(data).publish()
        assert ForecastModel.count() == num_forecasts + 1
        assert ObservationModel.count() == num_observations + 1
        assert model.to_dict() == ForecastModel.from_id(model.id).to_dict()
        ForecastModel.delete(model.id)
        ObservationModel.delete(model.observation_id)
        assert ForecastModel.count() == num_forecasts
        assert ObservationModel.count() == num_observations
        with pytest.raises(ForecastModel.NotFound):
            ForecastModel.from_id(model.id)
        with pytest.raises(ObservationModel.NotFound):
            ObservationModel.from_id(model.observation_id)

