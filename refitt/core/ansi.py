# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""ANSI escape sequences for colorizing text output."""


# standard library
import functools

# public interface
__all__ = ['ANSI_RESET', 'ANSI_CODES', 'colorize',
           'red', 'green', 'yellow', 'blue', 'magenta', 'cyan']


# escape sequences
ANSI_RESET = '\033[0m'
ANSI_CODES = {
    prefix: {
        color: '\033[{prefix}{num}m'.format(prefix=i + 3, num=j)
        for j, color in enumerate(['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'])
    }
    for i, prefix in enumerate(['foreground', 'background'])
}


def colorize(text: str, color: str) -> str:
    """Apply a foreground `color` code to the given `text`."""
    return ANSI_CODES['foreground'][color] + text + ANSI_RESET


# named color formats format
red = functools.partial(colorize, color='red')
green = functools.partial(colorize, color='green')
yellow = functools.partial(colorize, color='yellow')
blue = functools.partial(colorize, color='blue')
magenta = functools.partial(colorize, color='magenta')
cyan = functools.partial(colorize, color='cyan')
