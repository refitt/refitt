# Copyright (c) ITaP Research Computing. Purdue University 2019.
# Geoffrey Lentner <glentner@purdue.edu>.

"""Tools for searching the filesystem."""

# standard libs
import os
import functools
from typing import Generator


def _search(toplevel: str = '.') -> Generator[None, str, None]:
    """Yield back file paths under `toplevel`."""
    fullpath = functools.partial(os.path.join, toplevel)
    yield from map(fullpath, os.listdir(toplevel))


def _search_recursive(toplevel: str = '.', maxdepth: int = -1) -> Generator[None, str, None]:
    """Yield back file paths under `toplevel` recursively."""
    for root, subdirs, files in os.walk(toplevel):
        fullpath = functools.partial(os.path.join, toplevel)
        yield from map(fullpath, sorted(subdirs + files))
