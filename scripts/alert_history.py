#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019-2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Chart alert ingest frequency over time."""


# type annotations
from __future__ import annotations
from typing import List, IO, Union, Optional

# standard libs
import os
import sys
import logging
from functools import cached_property
from dataclasses import dataclass
from datetime import datetime

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface
from pandas import DataFrame, Series, Timestamp
from matplotlib import pyplot as plot
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# internal libs
import refitt  # noqa: import to trigger logging setup

# public interface
__all__ = ['LogRecord', 'LogData', 'AlertChart', 'AlertHistoryApp', ]


log = logging.getLogger('refitt')


@dataclass
class LogRecord:
    """Semi-structured data class for log records."""

    date: str
    time: str
    hostname: str
    level: str
    topic: str
    message: str

    @classmethod
    def from_line(cls, text: str) -> LogRecord:
        """Parse elements of a line of `text` to a `LogRecord`."""
        date, time, hostname, level, topic, *message = text.strip().split()
        return cls(date, time, hostname, level, topic, ' '.join(message))


class LogData:
    """Container list for log records."""

    __freq: str = '5Min'
    __records: List[LogRecord]

    def __init__(self, records: Union[List[LogRecord], LogData] = None, freq: str = __freq) -> None:
        """Direct initialization."""
        self.records = records
        self.freq = freq

    @property
    def records(self) -> List[LogRecord]:
        return self.__records

    @records.setter
    def records(self, other: Optional[List[LogRecord]]) -> None:
        """Verify log records."""
        if other is None:
            self.__records = []
        elif isinstance(other, list):
            for i, record in enumerate(other):
                if not isinstance(record, LogRecord):
                    raise TypeError(f'Expected type LogRecord, '
                                    f'found {record.__class__.__name__}{record} at position {i + 1}')
            else:
                self.__records = other
        else:
            raise TypeError('LogData.records expects a list of type LogRecord')

    @property
    def freq(self) -> str:
        return self.__freq

    @freq.setter
    def freq(self, other: str) -> None:
        """Ensure `str` for `freq`."""
        self.__freq = str(other)

    @classmethod
    def from_io(cls, stream: IO, freq: str = __freq) -> LogData:
        """Build LogData from existing I/O `stream`."""
        return cls(list(map(LogRecord.from_line, stream)), freq=freq)

    @classmethod
    def from_local(cls, filepath: str, freq: str = __freq, **options) -> LogData:
        """Build LogData by reading from disk with `filepath`."""
        with open(filepath, mode='r', **options) as stream:
            return cls.from_io(stream, freq=freq)

    @cached_property
    def dataframe(self) -> DataFrame:
        """Log records represented as a `pandas.DataFrame`."""
        log.info('Building data frame of log records')
        return DataFrame(self.records)

    @cached_property
    def datetime(self) -> Series:
        """Datetime64[ns] representation of date+time columns."""
        log.info('Processing date and time values')
        return (self.dataframe.date + ' ' + self.dataframe.time).astype('datetime64[ns]')

    @cached_property
    def structured_data(self) -> DataFrame:
        """Apply datetime values as index."""
        return self.dataframe[[]].assign(timestamp=self.datetime)

    @cached_property
    def sampled_data(self) -> DataFrame:
        """Resampled data frame on some frequency totals."""
        log.info(f'Re-sampling data on {self.freq} totals')
        return self.structured_data.assign(count=1).set_index('timestamp').resample(self.freq).sum()


class AlertChart:
    """Create, render, and save alert ingest history charts."""

    data: LogData
    freq: str = '5Min'
    figure: Figure
    ax: Axes
    title: str

    def __init__(self, data: LogData, freq: str = freq) -> None:
        """Initialize graph."""
        self.data = data
        self.freq = freq
        self.title = f'Antares Alert Ingest History: {freq} Totals'
        self.figure = plot.figure(self.title, figsize=(10, 5))
        self.figure.set_facecolor('white')
        self.ax = self.figure.add_axes([0.10, 0.15, 0.80, 0.75])

    def draw(self) -> None:
        """Render chart."""

        line_format = dict(color='steelblue', lw=1, alpha=1, zorder=40)
        self.data.sampled_data.plot(y='count', ax=self.ax, legend=False, **line_format)

        for side in 'top', 'bottom', 'left', 'right':
            self.ax.spines[side].set_color('gray')
            self.ax.spines[side].set_alpha(0.50)

        self.ax.set_xlim(right=Timestamp(datetime.now()))  # noqa: type
        self.ax.grid(True, axis='y', which='major', color='gray', lw=1, alpha=0.25, zorder=10)
        self.ax.grid(True, axis='y', which='minor', color='gray', lw=0.5, alpha=0.25, zorder=10)
        self.ax.grid(True, axis='x', which='major', color='gray', lw=1, alpha=0.25, zorder=10)
        self.ax.grid(True, axis='x', which='minor', color='gray', lw=0.5, alpha=0.25, zorder=10)
        self.ax.tick_params(axis='both', which='both', direction='in', length=0)
        self.ax.set_xlabel('Time', x=1, ha='right', fontsize=10, fontweight='semibold')
        self.ax.set_ylabel(f'Alerts Received ({self.freq})', y=1, ha='right',
                           fontsize=10, labelpad=10, fontweight='semibold')
        self.ax.set_title(self.title, fontsize=14, x=0, ha='left', va='bottom', fontweight='semibold')

    def save(self, *args, **kwargs) -> None:
        """Save figure to local file system."""
        self.figure.savefig(*args, **kwargs)


PROGRAM = 'alert-history'
USAGE = f"""\
usage: {PROGRAM} [-h] LOGFILE [-i] [-o PATH] ...
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-f, --frequency   FREQ  Resampling frequency (default: 5min).
-i, --interactive       Display live figure.
-o, --output      PATH  Path to save figure as file.
    --print             Print output to console.
-h, --help              Show this message and exit.\
"""


class AlertHistoryApp(Application):
    """Application class for requests module."""

    interface = Interface(PROGRAM, USAGE, HELP)

    source: str
    interface.add_argument('source')

    freq: str = '5Min'
    interface.add_argument('-f', '--frequency', default=freq, dest='freq')

    output: str
    interface.add_argument('-o', '--output', default=None)

    interactive_mode: bool = False
    interface.add_argument('-i', '--interactive', action='store_true', dest='interactive_mode')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    def run(self) -> None:
        """Run application."""
        data = self.load(self.source)
        chart = AlertChart(data, self.freq)
        chart.draw()
        if self.interactive_mode:
            plot.show()
        if self.output:
            chart.save(self.output)

    def load(self, filepath: str) -> LogData:
        """Load logging data."""
        if filepath == '-':
            return LogData.from_io(sys.stdin, self.freq)
        else:
            return LogData.from_local(filepath, self.freq)

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)


if __name__ == '__main__':
    sys.exit(AlertHistoryApp.main(sys.argv[1:]))
