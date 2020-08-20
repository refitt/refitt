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
from setuptools import setup, find_packages

# metadata
from refitt.__meta__ import (__appname__, __version__, __authors__,
                             __contact__, __license__, __description__,
                             __keywords__, __website__, __developer__)


with open('README.rst', mode='r') as readme:
    long_description = readme.read()


setup(
    name                 = __appname__,
    version              = __version__,
    author               = __developer__,
    author_email         = __contact__,
    description          = __description__,
    license              = __license__,
    keywords             = __keywords__,
    url                  = __website__,
    packages             = find_packages(),
    include_package_data = True,  # see MANIFEST.in
    long_description     = long_description,
    long_description_content_type = 'text/x-rst',
    classifiers          = ['Development Status :: 4 - Beta',
                            'Topic :: Scientific/Engineering :: Astronomy',
                            'Programming Language :: Python :: 3',
                            'Programming Language :: Python :: 3.7',
                            'Programming Language :: Python :: 3.8',
                            'Operating System :: POSIX :: Linux', ],
    entry_points         = {'console_scripts': ['refitt=refitt.apps.refitt:main',
                                                'refittd=refitt.apps.refittd:main',
                                                'refittctl=refitt.apps.refittctl:main']},
    install_requires     = [
        'numpy>=1.18.5', 'scipy>=1.4.1', 'pandas>=1.1.0', 'h5py>=2.10.0', 'xlrd>=1.2.0', 'tabulate>=0.8.7',
        'sqlalchemy>=1.3.19', 'psycopg2>=2.8.5', 'paramiko>=2.7.1', 'sshtunnel>=0.1.5',
        'flask>=1.1.2', 'gunicorn>=20.0.4', 'requests>=2.24.0',
        'cmdkit>=1.5.4', 'logalpha>=2.0.2', 'toml>=0.10.1',
        'antares-client<1', 'slackclient>=2.8.0',
        'tensorflow>=2.3.0', 'keras>=2.4.3',
        'pyarrow>=1.0.0', 'feather-format>=0.4.1'],
    extras_require       = {
        'dev': ['pytest>=6.0.1', 'pytest-cov>=2.10.1', 'hypothesis>=5.26.1', 'ipython>=7.17.0',
                'pylint>=2.5.3', 'sphinx>=3.2.1', 'pydata-sphinx-theme>=0.3.1', 'twine>=3.2.0']},
)
