# SPDX-FileCopyrightText: 2021 REFITT Team
# SPDX-License-Identifier: Apache-2.0

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
        'numpy', 'scipy', 'pandas', 'h5py', 'tables', 'pyarrow>=3.0.0',
        'sqlalchemy', 'psycopg2',
        'flask', 'gunicorn', 'requests', 'cryptography>=3.2.1',
        'cmdkit>=2.1.3', 'toml', 'streamkit>=0.3.2', 'names_generator>=0.1.0',
        'astropy>=4.0.1', 'antares-client>=1.0.1', 'slackclient>=2.8.0',
        'matplotlib', 'seaborn', 'rich',
        'tensorflow>=2.4.1',
        'parsl', 'astroplan', 'timezonefinder', 'pytz', 'bs4', 'jinja2',
    ],
)
