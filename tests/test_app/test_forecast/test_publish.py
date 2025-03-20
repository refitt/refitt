# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for forecast publishing app."""


# type annotations
from __future__ import annotations

# external libs
from pytest import mark, CaptureFixture

# internal libs
from refitt.admin.forecast.publish import ForecastPublishApp


class TestForecastPublishApp:
    """Test forecast publish workflows."""

    @mark.integration
    def test_usage(self: TestForecastPublishApp, capsys: CaptureFixture) -> None:
        """Print usage statement when no arguments are given."""
        ForecastPublishApp.main([])
        out, err = capsys.readouterr()
        assert out.strip() == ForecastPublishApp.interface.usage_text.strip()
        assert err == ''

    @mark.integration
    @mark.parametrize('flag', ['-h', '--help'])
    def test_help(self: TestForecastPublishApp, capsys: CaptureFixture, flag: str) -> None:
        """Print help statement when -h/--help is given."""
        ForecastPublishApp.main([flag, ])
        out, err = capsys.readouterr()
        assert out.strip() == ForecastPublishApp.interface.help_text.strip()
        assert err == ''
