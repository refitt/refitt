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

"""Unit tests for forecast interface."""


# type annotations
from typing import Dict, Any

# standard libs
import io
import json
import string
import random

# external libs
import numpy as np
from astropy.time import Time

# internal libs
from refitt.forecast import Forecast


def generate_random_forecast() -> Dict[str, Any]:
    """Generate random numbers to satisfy schema."""
    return {
        # NOTE: ztf_id fixed because the object needs to exist for integration tests
        'ztf_id': 'ZTF20actrfli',
        'instrument': 'ZTF_public',
        'time_since_trigger': random.randint(1, 20),
        'current_time': random.uniform(59_260, 60_000),
        'num_obs': random.randint(3, 20),
        'filter': random.choice(['g-ztf', 'r-ztf']),
        'class': [random.choices(string.ascii_uppercase, k=3), random.random()],
        'phase': 'rising',
        'next_mag_mean': random.uniform(14, 20),
        'next_mag_sigma': random.random(),
        'time_to_peak': list(map(float, np.random.rand(3))),
        'time_arr': list(map(float, np.random.rand(100))),
        'mag_mean': list(map(float, np.random.rand(100))),
        'mag_sigma': list(map(float, np.random.rand(100))),
        'mdmc': random.random(),
        'moe': random.random(),
    }


class TestForecast:
    """Unit tests against basic forecast interface."""

    def test_init(self) -> None:
        """Check instance creation."""
        data = generate_random_forecast()
        forecast = Forecast(data)
        assert forecast.data == data

    def test_init_from_forecast(self) -> None:
        """Test passive type coercion."""
        data = generate_random_forecast()
        forecast = Forecast(data)
        assert forecast == Forecast(forecast)

    def test_from_dict(self) -> None:
        """Test forecast initialization from existing dictionary."""
        data = generate_random_forecast()
        assert Forecast.from_dict(data).data == data

    def test_to_dict(self) -> None:
        """Test export to dictionary."""
        data = generate_random_forecast()
        assert Forecast.from_dict(data).to_dict() == data

    def test_equality(self) -> None:
        """Test equality comparison operator."""
        data = generate_random_forecast()
        assert Forecast.from_dict(data) == Forecast.from_dict(data)
        assert Forecast.from_dict(data) != Forecast.from_dict(generate_random_forecast())

    def test_from_str(self) -> None:
        """Test forecast initialization from existing string."""
        data = generate_random_forecast()
        text = json.dumps(data)
        assert Forecast.from_str(text).data == data

    def test_from_io(self) -> None:
        """Test forecast initialization from existing file descriptor."""
        data = generate_random_forecast()
        text = json.dumps(data)
        stream = io.StringIO(text)
        assert Forecast.from_io(stream).data == data

    def test_from_local(self, tmpdir: str) -> None:
        """Test forecast initialization from local file."""
        data = generate_random_forecast()
        with open(f'{tmpdir}/forecast.json', mode='w') as stream:
            json.dump(data, stream)
        assert Forecast.from_local(f'{tmpdir}/forecast.json').data == data

    def test_to_local(self, tmpdir: str) -> None:
        """Test forecast export to local file."""
        data = generate_random_forecast()
        Forecast.from_dict(data).to_local(f'{tmpdir}/forecast.json')
        with open(f'{tmpdir}/forecast.json', mode='r') as stream:
            assert json.load(stream) == data

    def test_attributes(self) -> None:
        """Check attribute access."""
        data = generate_random_forecast()
        forecast = Forecast.from_dict(data)
        for field, value in data.items():
            assert getattr(forecast, field) == value

    def test_time(self) -> None:
        """Check time property."""
        data = generate_random_forecast()
        forecast = Forecast.from_dict(data)
        assert forecast.time == Time(forecast.current_time + 1, format='mjd', scale='utc').datetime
