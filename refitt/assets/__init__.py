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

"""
Assets/templates required by REFITT.
"""

# type annotations
from typing import IO, Union

# standard libs
import os

# internal libs
from ..core.logging import Logger


# module level logger
log = Logger.with_name(__name__)


# either bytes or str depending on how the file was opened
FileData = Union[str, bytes]


def open_asset(relative_path: str, mode: str = 'r', **kwargs) -> IO:
    """
    Open a file from the /assets subpackage.

    Arguments
    ---------
    relative_path: str
        The relative file path below /assets directory.

    mode: str (default: 'r')
        The mode to open the file with.

    **kwargs:
        Additional keyword arguments are passed to open.

    Returns
    -------
    file: IO
        The file descriptor for the open file asset.
    """
    dirname = os.path.dirname(__file__)
    filepath = os.path.join(dirname, relative_path)
    try:
        return open(filepath, mode=mode, **kwargs)
    except FileNotFoundError as error:
        log.error(f'missing /assets/{relative_path}')
        raise


def load_asset(relative_path: str, mode: str = 'r', **kwargs) -> FileData:
    """
    Load an asset from its `relative_path` below /assets.

    Arguments
    ---------
    relative_path: str
        The relative file path below /assets directory.

    mode: str (default: 'r')
        The mode to open the file with.

    **kwargs:
        Additional keyword arguments are passed to open.

    Returns
    -------
    content: Union[str, bytes]
        The content of the file (depends on the mode).
    """
    with open_asset(relative_path, mode=mode, **kwargs) as source:
        content = source.read()
        log.debug(f'loaded /assets/{relative_path}')
        return content
