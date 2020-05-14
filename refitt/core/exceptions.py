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

"""Exception handling."""

# type annotations
from typing import Callable


class CompletedCommand(Exception):
    """Lift exit_status of sub-commands `main` method."""


def log_and_exit(exc: Exception, logger: Callable[[str], None], status: int) -> int:
    """Log the exception arguments and return with `status`."""
    logger(' - '.join(exc.args))
    return status
