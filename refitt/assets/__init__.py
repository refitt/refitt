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

"""Assets/templates required by REFITT."""

# type annotations
from typing import List, Dict, IO, Union, Generator

# standard libs
import os
import re
import fnmatch
import functools
import logging


# initialize module level logger
log = logging.getLogger(__name__)


# either bytes or str depending on how the file was opened
FileData = Union[str, bytes]


# The absolute location of this directory.
# The trailing path separator is necessary for reconstituting relative paths.
DIRECTORY = os.path.dirname(__file__) + os.path.sep


def abspath(relative_path: str) -> str:
    """Construct the absolute path to the file within /assets."""
    path = relative_path.lstrip(os.path.sep)
    return os.path.normpath(os.path.join(DIRECTORY, path))


# do not yield non-asset paths
IGNORE_PATHS = r'.*\/(__init__.py$|__pycache__\/.*)'


def _iter_paths() -> Generator[str, None, None]:
    """Yield relative file paths below /assets"""
    ignore = re.compile(IGNORE_PATHS)
    for root, dirs, files in os.walk(DIRECTORY):
        yield from filter(lambda path: ignore.match(path) is None,
                          map(functools.partial(os.path.join, root), files))


def _match_glob(pattern: str, path: str) -> bool:
    """True if `path` matches `pattern`."""
    return fnmatch.fnmatch(path, pattern)


def _match_regex(pattern: str, path: str) -> bool:
    """True if `path` matches `pattern`."""
    return re.match(pattern, path) is not None


def find_files(pattern: str, regex: bool = False) -> List[str]:
    """List the assets matching a glob/regex `pattern`."""
    return sorted(filter(functools.partial(_match_glob if not regex else _match_regex, pattern),
                         map(lambda path: os.path.normpath(path).replace(DIRECTORY, ''), _iter_paths())))


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
    except FileNotFoundError:
        log.error(f'Missing /assets/{relative_path}')
        raise


@functools.lru_cache(maxsize=None)
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
        log.debug(f'Loaded /assets/{relative_path}')
        return content


def load_assets(pattern: str, regex: bool = False, **kwargs) -> Dict[str, FileData]:
    """
    Load all files matching `pattern`.

    Arguments
    ---------
    pattern: str
        Either a glob pattern or regular expression for the files to include.

    regex: bool (default: False)
        Whether to interpret the `pattern` as a regular expression.

    Returns
    -------
    file_data: Dict[str, Union[str, bytes]]
        A dictionary of the file data, indexed by the relative file path within
        the /assets directory. Use `mode='rb'` to return raw bytes data.
    """
    return {path: load_asset(path, **kwargs) for path in find_files(pattern, regex=regex)}
