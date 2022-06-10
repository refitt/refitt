# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for forecast interface."""


# type annotations
from __future__ import annotations
from typing import Type

# standard libs
import io
import json
import string
import random
from abc import ABC, abstractstaticmethod

# external libs
import numpy as np
# from astropy.time import Time
# from hypothesis import given, strategies as st

# internal libs
from refitt.core.typing import JsonDict
from refitt.core.schema import SchemaError
from refitt.data.forecast.model import ModelData
from refitt.data.forecast import ConvAutoEncoder, CoreCollapseInference


class ModelTestBase(ABC):

    model_type: Type[ModelData]

    @abstractstaticmethod
    def generate() -> JsonDict:
        """Generate randomized model data for testing purposes."""

    def test_init(self) -> None:
        """Check instance creation."""
        data = self.generate()
        forecast = self.model_type.from_dict(data)
        assert forecast.data == data

    def test_missing_key(self) -> None:
        """Will raise SchemaError on missing key."""
        data = self.generate()
        for key in self.model_type.schema.member_type.keys():  # noqa: member_type
            data_copy = data.copy()
            data_copy.pop(key)
            try:
                _ = self.model_type.from_dict(data_copy)
            except SchemaError as error:
                assert str(error) == f'Missing key \'{key}\''
            else:
                raise AssertionError('Expected SchemaError')

    def test_wrong_type_for_value(self) -> None:
        """Will raise SchemaError on wrong type for value."""
        data = self.generate()
        data['ztf_id'] = 123
        try:
            _ = self.model_type.from_dict(data)
        except SchemaError as error:
            assert str(error) == 'Expected type str for member \'ztf_id\', found int(123) at position 1'
        else:
            raise AssertionError('Expected SchemaError')

    def test_init_from_forecast(self) -> None:
        """Test passive type coercion."""
        data = self.generate()
        forecast = self.model_type.from_dict(data)
        assert forecast == self.model_type(forecast)

    def test_to_dict(self) -> None:
        """Test export to dictionary."""
        data = self.generate()
        assert self.model_type.from_dict(data).to_dict() == data

    def test_equality(self) -> None:
        """Test equality comparison operator."""
        data = self.generate()
        assert self.model_type.from_dict(data) == self.model_type.from_dict(data)
        assert self.model_type.from_dict(data) != self.model_type.from_dict(self.generate())

    def test_from_str(self) -> None:
        """Test forecast initialization from existing string."""
        data = self.generate()
        text = json.dumps(data)
        assert self.model_type.from_str(text).data == data

    def test_from_io(self) -> None:
        """Test forecast initialization from existing file descriptor."""
        data = self.generate()
        text = json.dumps(data)
        stream = io.StringIO(text)
        assert self.model_type.from_io(stream).data == data

    def test_from_local(self, tmpdir: str) -> None:
        """Test forecast initialization from local file."""
        data = self.generate()
        with open(f'{tmpdir}/forecast.json', mode='w') as stream:
            json.dump(data, stream)
        assert self.model_type.from_local(f'{tmpdir}/forecast.json').data == data

    def test_to_local(self, tmpdir: str) -> None:
        """Test forecast export to local file."""
        data = self.generate()
        self.model_type.from_dict(data).to_local(f'{tmpdir}/forecast.json')
        with open(f'{tmpdir}/forecast.json', mode='r') as stream:
            assert json.load(stream) == data

    def test_attributes(self) -> None:
        """Check attribute access."""
        data = self.generate()
        forecast = self.model_type.from_dict(data)
        for field, value in data.items():
            assert getattr(forecast, field) == value


class TestConvAutoEncoder(ModelTestBase):
    """Unit tests (mostly schema checks) for ConvAutoEncoder."""

    model_type = ConvAutoEncoder

    @staticmethod
    def generate() -> JsonDict:
        """Generate random numbers to satisfy schema."""
        return {
            # NOTE: ztf_id fixed because the object needs to exist for integration tests
            'model_type': 'conv_auto_encoder',
            'ztf_id': 'ZTF20actrfli',  # noqa: spelling
            'instrument': 'ZTF_public',
            'time_since_trigger': random.randint(1, 20),
            'mjd': random.uniform(59_260, 60_000),
            'num_obs': random.randint(3, 20),
            'filter': random.choice(['g-ztf', 'r-ztf']),
            'class': [['SN Ia', ], 0.793],
            'phase': 'rising',
            'next_mag_mean': random.uniform(14, 20),
            'next_mag_sigma': random.random(),
            'time_to_peak': list(map(float, np.random.rand(3))),
            'mjd_arr': list(map(float, np.random.rand(100))),
            'mag_arr': list(map(float, np.random.rand(100))),
            'err_arr': list(map(float, np.random.rand(100))),
            'mdmc': random.random(),
            'moe': random.random(),
        }


class TestCoreCollapseInference(ModelTestBase):
    """Unit tests (mostly schema checks) for ConvAutoEncoder."""

    model_type = CoreCollapseInference

    @staticmethod
    def generate() -> JsonDict:
        """Generate random numbers to satisfy schema."""
        mjd_arr = np.random.rand(100) * 2  # must contain mjd = (0.5 + 1)
        mjd_arr.sort()
        return {
            # NOTE: ztf_id fixed because the object needs to exist for integration tests
            'model_type': 'core_collapse_inference',
            'ztf_id': 'ZTF20actrfli',  # noqa: spelling
            'filter': random.choice(['g-ztf', 'r-ztf']),
            'mjd': 0.5,  # NOTE: statistically this should be fine (for interpolation)
            'mjd_arr': list(map(float, mjd_arr)),
            'mag_arr': [list(map(float, np.random.rand(100))) for _ in range(5)],
            'err_arr': list(map(float, np.random.rand(100))),
            'parameters': {
                'zams': list(map(float, np.random.rand(3))),
                'k_energy': list(map(float, np.random.rand(3))),
                'mloss_rate': list(map(float, np.random.rand(3))),
                'beta': list(map(float, np.random.rand(3))),
                '56Ni': list(map(float, np.random.rand(3))),
                'texp': list(map(float, np.random.rand(3))),
                'A_v': list(map(float, np.random.rand(3))),
            },
        }
