# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for forecast publishing app."""


# type annotations
from __future__ import annotations
# from typing import Type, Callable

# standard libs
from tempfile import TemporaryDirectory

# external libs
from pytest import mark, raises, CaptureFixture

# internal libs
from refitt.apps.refitt.forecast.publish import ForecastPublishApp
# from refitt.core.typing import JsonDict
# from refitt.database.model import Observation as ObservationModel, Model
# from refitt.forecast import ConvAutoEncoder, CoreCollapseInference
# from refitt.forecast.model import ModelData

# testing libs
# from tests.unit.test_forecast import ModelTestBase
# from tests.unit.test_forecast import TestConvAutoEncoder as _TestConvAutoEncoder
# from tests.unit.test_forecast import TestCoreCollapseInference as _TestCoreCollapseInference


@mark.integration
class TestForecastPublishApp:
    """Test forecast publish workflows."""

    def test_usage(self: TestForecastPublishApp, capsys: CaptureFixture) -> None:
        """Print usage statement when no arguments are given."""
        ForecastPublishApp.main([])
        out, err = capsys.readouterr()
        assert out.strip() == ForecastPublishApp.interface.usage_text.strip()
        assert err == ''

    @mark.parametrize('flag', ['-h', '--help'])
    def test_help(self: TestForecastPublishApp, capsys: CaptureFixture, flag: str) -> None:
        """Print help statement when -h/--help is given."""
        ForecastPublishApp.main([flag, ])
        out, err = capsys.readouterr()
        assert out.strip() == ForecastPublishApp.interface.help_text.strip()
        assert err == ''
