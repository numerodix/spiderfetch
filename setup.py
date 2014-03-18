import os

from setuptools import find_packages
from setuptools import setup

import spiderfetch


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='spiderfetch',
    version=spiderfetch.__version__,
    description='Web spider and fetcher',
    author='Martin Matusiak',
    author_email='numerodix@gmail.com',
    url='https://github.com/numerodix/spiderfetch',

    packages=find_packages('.'),
    package_dir = {'': '.'},

    install_requires=[
        'ansicolor',
    ],

    # don't install as zipped egg
    zip_safe=False,

    entry_points={
        "console_scripts": [
            "spiderfetch = spiderfetch.spiderfetch:run_script",
        ]
    },

    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
