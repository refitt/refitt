# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Forecast models provided by the REFITT system."""


# type annotations
from typing import Dict, Type, IO, Union

# standard libs
import json

# internal libs
from refitt.core.logging import Logger
from refitt.forecast.model import ModelData
from refitt.forecast.conv_auto_encoder import ConvAutoEncoder
from refitt.forecast.core_collapse_inference import CoreCollapseInference

# public interface
__all__ = ['model_types', 'load_model',
           'ConvAutoEncoder', 'CoreCollapseInference', ]

# module logger
log = Logger.with_name(__name__)


model_types: Dict[str, Type[ModelData]] = {
    ConvAutoEncoder.name: ConvAutoEncoder,
    CoreCollapseInference.name: CoreCollapseInference,
}


def load_model(file_or_stream: Union[str, IO]) -> ModelData:
    """Initialize model data from local file path (or existing IO stream)."""
    name = file_or_stream if isinstance(file_or_stream, str) else file_or_stream.name
    try:
        if isinstance(file_or_stream, str):
            with open(file_or_stream, mode='r') as stream:
                data = json.load(stream)
        else:
            data = json.load(file_or_stream)
    except Exception as exc:
        raise ModelData.Error(f'{exc} (from {name})') from exc
    if not isinstance(data, dict):
        raise ModelData.Error(f'Expected JSON dict (from {name}), found \'{type(data)}\'')
    if 'model_type' not in data:
        raise ModelData.Error(f'Missing \'model_type\' (from {name})')
    model_type = data['model_type']
    if model_type in model_types:
        model_data = model_types[model_type].from_dict(data)
        log.debug(f'Loaded {model_type} (from {name})')
        return model_data
    else:
        raise ModelData.Error(f'Unknown model type \'{model_type}\' (from {name})')
