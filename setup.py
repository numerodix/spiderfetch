from setuptools import find_packages
from setuptools import setup

import spiderfetch


setup(
    name='spiderfetch',
    version=spiderfetch.__version__,
    description='Web spider and fetcher',
    author='Martin Matusiak',
    author_email='numerodix@gmail.com',

    packages=find_packages('.'),
    package_dir = {'': '.'},

    # don't install as zipped egg
    zip_safe=False,

    entry_points={
        "console_scripts": [
            "spiderfetch = spiderfetch.spiderfetch:run_script",
        ]
    },
)
