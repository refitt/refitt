# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for observation publishing app."""


# type annotations
from __future__ import annotations

# standard libs
import os
import logging
from datetime import datetime
from tempfile import TemporaryDirectory

# external libs
import numpy as np
from astropy.io import fits
from pytest import mark, CaptureFixture, LogCaptureFixture

# internal libs
from refitt.apps.refitt.observation.publish import ObservationPublishApp
from refitt.database.model import Observation, Source, Object, File, Epoch


@mark.integration
class TestObservationPublishApp:
    """Test forecast publish workflows."""

    def test_usage(self: TestObservationPublishApp, capsys: CaptureFixture) -> None:
        """Print usage statement when no arguments are given."""
        ObservationPublishApp.main([])
        out, err = capsys.readouterr()
        assert out.strip() == ObservationPublishApp.interface.usage_text.strip()
        assert err == ''

    @mark.parametrize('flag', ['-h', '--help'])
    def test_help(self: TestObservationPublishApp, flag: str, capsys: CaptureFixture) -> None:
        """Print help statement when -h/--help is given."""
        ObservationPublishApp.main([flag, ])
        out, err = capsys.readouterr()
        assert out.strip() == ObservationPublishApp.interface.help_text.strip()
        assert err == ''

    args = ['tomb_raider_croft_4m', 'dreamy_awesome_kowalevski', 'clear', '15.72', '0.1']
    metavars = ['SOURCE', 'OBJECT', 'BAND', 'MAG', 'ERR']

    @mark.parametrize('pos', [1, 2, 3, 4])
    def test_missing_positional(self: TestObservationPublishApp, pos: int,
                                capsys: CaptureFixture, caplog: LogCaptureFixture) -> None:
        """Failure on missing positional argument."""
        with caplog.at_level(logging.DEBUG, logger='refitt'):
            ObservationPublishApp.main(self.args[:pos])
        out, err = capsys.readouterr()
        assert out == ''
        assert err == ''
        assert caplog.record_tuples == [
            ('refitt', logging.CRITICAL, 'the following arguments are required: ' + ', '.join(self.metavars[pos:])),
        ]

    def test_missing_mjd(self: TestObservationPublishApp,
                         capsys: CaptureFixture, caplog: LogCaptureFixture) -> None:
        """Failure on missing MJD if --file also missing."""
        with caplog.at_level(logging.DEBUG, logger='refitt'):
            ObservationPublishApp.main(self.args)
        out, err = capsys.readouterr()
        assert out == ''
        assert err == ''
        assert caplog.record_tuples == [
            ('refitt', logging.INFO, 'Latest epoch (4: 2020-10-27 20:01:00-04:00)'),
            ('refitt', logging.INFO, 'Resolved source (5: tomb_raider_croft_4m)'),
            ('refitt', logging.INFO, 'Resolved object (6: dreamy_awesome_kowalevski)'),
            ('refitt', logging.CRITICAL, 'No MJD provided')
        ]

    def test_with_mjd(self: TestObservationPublishApp,
                      capsys: CaptureFixture, caplog: LogCaptureFixture) -> None:
        """Successful execution of workflow with explicit MJD."""
        count = Observation.count()
        source_name = 'tomb_raider_croft_4m'
        object_name = 'dreamy_awesome_kowalevski'
        source = Source.from_name(source_name)
        object = Object.from_name(object_name)
        assert Observation.count() == count
        with caplog.at_level(logging.DEBUG, logger='refitt'):
            ObservationPublishApp.main([source_name, object_name, 'clear', '15.72', '0.1', '59780.414', '--print'])
            out, err = capsys.readouterr()
            obs_id = int(out.strip())

        assert err == ''
        assert caplog.record_tuples == [
            ('refitt', logging.INFO, 'Latest epoch (4: 2020-10-27 20:01:00-04:00)'),
            ('refitt', logging.INFO, f'Resolved source (5: {source_name})'),
            ('refitt', logging.INFO, f'Resolved object (6: {object_name})'),
            ('refitt.database.model', logging.DEBUG, f'Added observation ({obs_id})'),
            ('refitt', logging.INFO, f'Published observation ({obs_id})')
        ]

        observation = Observation.from_id(obs_id)
        assert Observation.count() == count + 1
        assert obs_id == observation.id
        assert observation.source.id == source.id
        assert observation.object.id == object.id

        Observation.delete(obs_id)
        assert Observation.count() == count

    def test_with_file_missing_mjd(self: TestObservationPublishApp,
                                   capsys: CaptureFixture, caplog: LogCaptureFixture) -> None:
        """Failed execution of workflow with local file missing MJD."""

        count = 78
        source_name = 'tomb_raider_croft_4m'
        object_name = 'dreamy_awesome_kowalevski'
        assert Observation.count() == count

        prev_file = File.from_id(1)
        with TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, prev_file.name)
            with open(filepath, mode='wb') as stream:
                stream.write(prev_file.data)

            with caplog.at_level(logging.DEBUG, logger='refitt'):
                ObservationPublishApp.main([source_name, object_name, 'clear', '15.72', '0.1',
                                            '--file', filepath, '--print'])
                out, err = capsys.readouterr()
                # obs_id = int(out.strip())

        assert err == ''
        assert caplog.record_tuples == [
            ('refitt', logging.INFO, 'Latest epoch (4: 2020-10-27 20:01:00-04:00)'),
            ('refitt', logging.INFO, f'Resolved source (5: {source_name})'),
            ('refitt', logging.INFO, f'Resolved object (6: {object_name})'),
            ('refitt', logging.CRITICAL,
             f'RuntimeError: Missing DATE-OBS in header ({prev_file.name})'),
        ]

    def test_with_file(self: TestObservationPublishApp,
                       capsys: CaptureFixture, caplog: LogCaptureFixture) -> None:
        """Successful execution of workflow with local file having MJD."""

        count = 78
        source_name = 'tomb_raider_croft_4m'
        object_name = 'dreamy_awesome_kowalevski'
        source = Source.from_name(source_name)
        object = Object.from_name(object_name)
        epoch = Epoch.latest()
        assert Observation.count() == count

        with TemporaryDirectory() as tmpdir:

            data = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3]])
            filepath = os.path.join(tmpdir, 'observation.fits.gz')

            mjd = str(datetime.utcnow())
            hdu = fits.PrimaryHDU(data)
            hdu.header['DATE-OBS'] = mjd
            hdu.writeto(filepath)

            assert np.allclose(data, fits.getdata(filepath))

            with caplog.at_level(logging.DEBUG, logger='refitt'):
                ObservationPublishApp.main([source_name, object_name, 'clear', '15.72', '0.1',
                                            '--file', filepath, '--print'])
                out, err = capsys.readouterr()
                obs_id = int(out.strip())

        file_id = File.from_observation(obs_id).id

        assert err == ''
        assert caplog.record_tuples == [
            ('refitt', logging.INFO, f'Latest epoch ({epoch.id}: {epoch.created})'),
            ('refitt', logging.INFO, f'Resolved source ({source.id}: {source_name})'),
            ('refitt', logging.INFO, f'Resolved object ({object.id}: {object_name})'),
            ('refitt', logging.INFO, f'Extracted MJD ({mjd}) from file ({filepath})'),
            ('refitt.database.model', logging.DEBUG, f'Added observation ({obs_id})'),
            ('refitt', logging.INFO, f'Published observation ({obs_id})'),
            ('refitt', logging.INFO, 'Uploading file (observation.fits.gz)'),
            ('refitt.database.model', logging.DEBUG, f'Added file ({file_id})')
        ]

        File.delete(file_id)
        observation = Observation.from_id(obs_id)
        assert Observation.count() == count + 1
        assert obs_id == observation.id
        assert observation.source.id == source.id
        assert observation.object.id == object.id

        Observation.delete(obs_id)
        assert Observation.count() == count
