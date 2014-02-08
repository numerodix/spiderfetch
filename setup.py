from setuptools import setup, find_packages

setup(
    name='spiderfetch',
    version='0.1',
    description='Web spider and fetcher',
    author='Martin Matusiak',
    author_email='numerodix@gmail.com',

    packages=find_packages('.'),
    package_dir = {'': '.'},

    # don't install as zipped egg
    zip_safe=False,
)
