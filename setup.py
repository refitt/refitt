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
import re
from setuptools import setup, find_packages


# get long description from README.rst
with open('README.rst', mode='r') as readme:
    long_description = readme.read()


# get package metadata by parsing __meta__ module
with open('refitt/__meta__.py', mode='r') as source:
    content = source.read().strip()
    metadata = {key: re.search(key + r'\s*=\s*[\'"]([^\'"]*)[\'"]', content).group(1)
                for key in ['__version__', '__developer__', '__contact__',
                            '__description__', '__license__', '__keywords__', '__website__']}


setup(
    name                 = 'refitt',
    version              = metadata['__version__'],
    author               = metadata['__developer__'],
    author_email         = metadata['__contact__'],
    description          = metadata['__description__'],
    license              = metadata['__license__'],
    keywords             = metadata['__keywords__'],
    url                  = metadata['__website__'],
    packages             = find_packages(),
    include_package_data = True,  # see MANIFEST.in
    long_description     = long_description,
    long_description_content_type = 'text/x-rst',
    classifiers          = ['Development Status :: 4 - Beta',
                            'Topic :: Scientific/Engineering :: Astronomy',
                            'Programming Language :: Python :: 3',
                            'Programming Language :: Python :: 3.8',
                            'Programming Language :: Python :: 3.9',
                            'Programming Language :: Python :: 3.10',
                            'Operating System :: POSIX :: Linux', ],
    entry_points         = {'console_scripts': ['refitt=refitt.apps.refitt:main',
                                                'refittd=refitt.apps.refittd:main',
                                                'refittctl=refitt.apps.refittctl:main']},
    install_requires     = [
        'numpy>=1.18.5', 'scipy>=1.4.1', 'pandas>=1.1.0', 'pyarrow>=3.0.0',
        'sqlalchemy>=1.3.19', 'psycopg2>=2.8.5',
        'flask>=1.1.2', 'gunicorn>=20.0.4', 'requests>=2.24.0', 'cryptography>=3.2.1',
        'cmdkit>=2.1.3', 'toml>=0.10.2', 'streamkit>=0.3.2', 'names_generator>=0.1.0',
        'astropy>=4.0.1', 'antares-client>=1.0.1', 'slackclient>=2.8.0',
        'matplotlib>=3.3.2', 'seaborn>=0.11.0', 'rich>=9.4.0',
        'tensorflow>=2.4'
    ],
)
