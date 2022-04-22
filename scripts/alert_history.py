#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Create graph of alert ingest frequency over time."""


# type annotations
from __future__ import annotations
from typing import List, IO, Union

# standard libs
import os
import sys
import logging
from functools import cached_property
from datetime import datetime
from dataclasses import dataclass

# external libs
from cmdkit.app import Application
from cmdkit.cli import Interface
from pandas import DataFrame, Timestamp
from matplotlib import pyplot as plot
from matplotlib.figure import Figure
from matplotlib.axes import Axes

# internal libs
from refitt.database.model import Observation, Source
from refitt.database.interface import Session


# public interface
__all__ = ['LogData', 'AlertChart', 'AlertHistoryApp', ]


log = logging.getLogger('refitt')
Application.log_critical = log.critical
Application.log_exception = log.critical


@dataclass
class LogData:
    """Container list for log records."""

    records: List[datetime]

    @classmethod
    def from_database(cls, since: Union[str, datetime] = '2022-01-01') -> LogData:
        """Query database for timestamps of accepted alerts."""
        antares = Source.from_name('antares')
        since = since if isinstance(since, datetime) else datetime.fromisoformat(since)
        log.info(f'Searching for alerts since {since}')
        return cls([
            ts for (ts, ) in (
                Session.query(Observation.recorded)
                    .filter(Observation.recorded >= since.astimezone(),
                            Observation.source_id == antares.id)
                    .order_by(Observation.recorded)
                    .all()
            )
        ])


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

        log.info(f'Aggregating events on {self.freq} basis')
        local_tz = datetime.now().astimezone().tzinfo
        data = DataFrame({'time': [dt.astimezone(local_tz).replace(tzinfo=None) for dt in self.data.records]})
        data = data.sort_values(by='time').set_index('time').assign(count=1)
        data = data.resample(self.freq).sum()

        line_format = dict(color='steelblue', lw=1, alpha=1, zorder=40)
        data.plot(y='count', ax=self.ax, legend=False, **line_format)

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
usage: {PROGRAM} [-h] [-i] [-o PATH] [-s DATE] [-f FREQ] [--print]
{__doc__}\
"""

HELP = f"""\
{USAGE}

options:
-f, --frequency   FREQ  Resampling frequency (default: 5min).
-s, --since       DATE  Date in ISO format (default: 2022-01-01).
-i, --interactive       Display live figure.
-o, --output      PATH  Path to save figure as file.
    --print             Print output to console.
-h, --help              Show this message and exit.\
"""


class AlertHistoryApp(Application):
    """Application class for requests module."""

    interface = Interface(PROGRAM, USAGE, HELP)

    freq: str = '5Min'
    interface.add_argument('-f', '--frequency', default=freq, dest='freq')

    since: datetime = datetime.fromisoformat('2022-01-01')
    interface.add_argument('-s', '--since', type=datetime.isoformat, default=since)

    output: str
    interface.add_argument('-o', '--output', default=None)

    interactive_mode: bool = False
    interface.add_argument('-i', '--interactive', action='store_true', dest='interactive_mode')

    verbose: bool = False
    interface.add_argument('--print', action='store_true', dest='verbose')

    def run(self) -> None:
        """Run application."""
        data = LogData.from_database(since=self.since)
        log.info(f'Found {len(data.records)} events')
        chart = AlertChart(data, self.freq)
        chart.draw()
        if self.interactive_mode:
            plot.show()
        if self.output:
            chart.save(self.output)

    @cached_property
    def output(self) -> IO:
        """File descriptor for writing output."""
        return sys.stdout if self.verbose else open(os.devnull, mode='w')

    def write(self, *args, **kwargs) -> None:
        """Write output to stream."""
        print(*args, **kwargs, file=self.output)


if __name__ == '__main__':
    sys.exit(AlertHistoryApp.main(sys.argv[1:]))
