# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for forecast interface."""


# type annotations
from __future__ import annotations
from typing import Type, Callable

# external libs
import pytest

# internal libs
from refitt.core.typing import JsonDict
from refitt.database.model import Observation as ObservationModel, Model
from refitt.data.forecast import ConvAutoEncoder, CoreCollapseInference
from refitt.data.forecast.model import ModelData

# testing libs
from tests.unit.test_forecast import ModelTestBase
from tests.unit.test_forecast import TestConvAutoEncoder as _TestConvAutoEncoder
from tests.unit.test_forecast import TestCoreCollapseInference as _TestCoreCollapseInference


class ForecastPublishTestBase:
    """Tests for database integration with forecast interface."""

    model_type: Type[ModelData]
    testing: Type[ModelTestBase]

    def generate(self) -> JsonDict:
        return self.testing.generate()

    def test_publish(self) -> None:
        """Publish model in single invocation as primary observation."""

        data = self.generate()
        num_forecasts = Model.count()
        num_observations = ObservationModel.count()

        model = self.model_type.from_dict(data).publish()
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

    def test_publish_observation(self) -> None:
        """Publish only the observation."""

        data = self.generate()
        num_forecasts = Model.count()
        num_observations = ObservationModel.count()

        observation = self.model_type.from_dict(data).publish_observation()
        assert Model.count() == num_forecasts
        assert ObservationModel.count() == num_observations + 1

        ObservationModel.delete(observation.id)
        assert Model.count() == num_forecasts
        assert ObservationModel.count() == num_observations
        with pytest.raises(ObservationModel.NotFound):
            ObservationModel.from_id(observation.id)

    def test_publish_with_existing_observation(self) -> None:
        """Publish a model with an existing observation."""

        data = self.generate()
        num_forecasts = Model.count()
        num_observations = ObservationModel.count()

        observation = self.model_type.from_dict(data).publish_observation()
        assert Model.count() == num_forecasts
        assert ObservationModel.count() == num_observations + 1

        model = self.model_type.from_dict(data).publish(observation_id=observation.id)
        assert Model.count() == num_forecasts + 1
        assert ObservationModel.count() == num_observations + 1
        assert model.to_dict() == Model.from_id(model.id).to_dict()
        assert model.observation_id == observation.id

        Model.delete(model.id)
        ObservationModel.delete(observation.id)
        assert Model.count() == num_forecasts
        assert ObservationModel.count() == num_observations

        with pytest.raises(Model.NotFound):
            Model.from_id(model.id)
        with pytest.raises(ObservationModel.NotFound):
            ObservationModel.from_id(model.observation_id)


class TestPublishConvAutoEncoder(ForecastPublishTestBase):
    """Test publishing of forecast."""

    model_type = ConvAutoEncoder
    testing = _TestConvAutoEncoder


class TestPublishCoreCollapseInference(ForecastPublishTestBase):
    """Test publishing of forecast."""

    model_type = CoreCollapseInference
    testing = _TestCoreCollapseInference
