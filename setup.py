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

"""Setup and installation script for refitt."""

# standard libs
import os
from setuptools import setup, find_packages

# metadata
from refitt.__meta__ import (__appname__, __version__, __authors__,
                             __contact__, __license__, __description__,
                             __keywords__, __website__)


def readme_file():
    """Use README.md as long_description."""
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r') as readme:
        return readme.read()


console_apps = {
    'refitt': 'refitt.apps.refitt:main',
    'refittd': 'refitt.apps.refittd:main',
    'refittctl': 'refitt.apps.refittctl:main'
}

setup(
    name                 = __appname__,
    version              = __version__,
    author               = __authors__,
    author_email         = __contact__,
    description          = __description__,
    license              = __license__,
    keywords             = __keywords__,
    url                  = __website__,
    packages             = find_packages(),
    include_package_data = True,
    long_description     = readme_file(),
    classifiers          = ['Development Status :: 4 - Beta',
                            'Topic :: Scientific/Engineering :: Astronomy',
                            'Programming Language :: Python :: 3.7', ],
    entry_points         = {'console_scripts': [
        f'{name}={method}' for name, method in console_apps.items()
    ]},
)
