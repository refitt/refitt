# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Convolutional auto-encoder built on RESNET-50."""


# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import functools

# internal libs
from refitt.core.schema import ListSchema
from refitt.core.logging import Logger
from refitt.database.model import ObjectType
from refitt.forecast.model import ModelData, ModelSchema

# public interface
__all__ = ['ConvAutoEncoder', ]

# module logger
log = Logger.with_name(__name__)


@functools.lru_cache(maxsize=None)
def get_object_type(name: str) -> ObjectType:
    """Fetch and cache `object_type.id` given `name`."""
    try:
        return ObjectType.from_name(name)
    except ObjectType.NotFound as exc:
        log.error(f'Object type not found ({name}) - trying again (with \'SN {name}\')')
        return ObjectType.from_name(f'SN {name}')


class ConvAutoEncoder(ModelData):
    """
    The principle forecast data used by REFITT.

    This forecast output is used to initialize the observation linked
    by all other models (at the moment).

    See Also:
        refitt-forecast (package)
    """

    name = 'conv_auto_encoder'
    schema = ModelSchema.of({
        'model_type': str,
        'ztf_id': str,
        'instrument': str,
        'time_since_trigger': float,
        'mjd': float,
        'num_obs': int,
        'filter': str,  # e.g., 'g-ztf'
        'class': ListSchema.any(),  # FIXME: we should use a different structure here
        'phase': str,
        'next_mag_mean': float,
        'next_mag_sigma': float,
        'time_to_peak': ListSchema.of(float),
        'mjd_arr': ListSchema.of(float),
        'mag_arr': ListSchema.of(float),
        'err_arr': ListSchema.of(float),
        'mdmc': float,
        'moe': float
    })

    @property
    def observation_value(self: ConvAutoEncoder) -> Optional[float]:
        """Value for published observation record."""
        return self.next_mag_mean

    @property
    def observation_error(self: ConvAutoEncoder) -> Optional[float]:
        """Error for published observation record."""
        return self.next_mag_sigma

    @property
    def object_pred_type(self: ConvAutoEncoder) -> Optional[dict]:
        """Predicted object type name (e.g., {'name': 'Ia', 'score': 0.74})."""
        types, *scores = self.data['class']
        obj_type = get_object_type(types[0])
        return {
            'id': obj_type.id,
            'name': obj_type.name,
            'score': round(float(scores[0]), 4),
        }
