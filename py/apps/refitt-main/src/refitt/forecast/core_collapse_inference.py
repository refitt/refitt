# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Core collapse inference model with many realizations."""


# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import functools

# external libs
from scipy.interpolate import interp1d

# internal libs
from refitt.core.schema import ListSchema, DictSchema, Size
from refitt.forecast.model import ModelData, ModelSchema

# public interface
__all__ = ['CoreCollapseInference', ]


class CoreCollapseInference(ModelData):
    """
    Core collapse inference model with many realizations.
    This model is not currently the principle model.
    """

    name = 'core_collapse_inference'
    schema = ModelSchema.of({
        'model_type': str,
        'ztf_id': str,
        'filter': str,  # e.g., "g-ztf" or "r-ztf"
        'mjd_arr': ListSchema.of(float),
        'mag_arr': ListSchema.of(ListSchema.of(float, size=Size.ALL_EQUAL)),
        'err_arr': ListSchema.of(float),
        'mjd': float,
        'parameters': DictSchema.of({
            'zams': ListSchema.of(float, size=3),  # mean, lower, upper
            'k_energy': ListSchema.of(float, size=3),
            'mloss_rate': ListSchema.of(float, size=3),
            'beta': ListSchema.of(float, size=3),
            '56Ni': ListSchema.of(float, size=3),
            'texp': ListSchema.of(float, size=3),
            'A_v': ListSchema.of(float, size=3),
        }),
    })

    @functools.cached_property
    def observation_value(self: CoreCollapseInference) -> Optional[float]:
        """Value for published observation record."""
        f = interp1d(self.mjd_arr, self.mag_arr[0])
        return float(f(self.mjd + 1))

    @functools.cached_property
    def observation_error(self: CoreCollapseInference) -> Optional[float]:
        """Error for published observation record."""
        return None

    @property
    def object_pred_type(self: CoreCollapseInference) -> Optional[dict]:
        """Always None because this model does not predict type."""
        return None
