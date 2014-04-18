spiderfetch
===========

.. image:: https://badge.fury.io/py/spiderfetch.png
        :target: https://badge.fury.io/py/spiderfetch

.. image:: https://travis-ci.org/numerodix/spiderfetch.png?branch=master
    :target: https://travis-ci.org/numerodix/spiderfetch


Installation
------------

.. code:: bash

    $ pip install spiderfetch
    $ spiderfetch


Usage
-----


Fetching
^^^^^^^^

Fetch all urls matching ``2008.*.ogg`` from a page:

.. code:: bash

    $ spiderfetch http://www.fosdem.org/2008/media/video 2008.*ogg

To dump the urls to a file instead of fetching:

.. code:: bash

    $ spiderfetch http://www.fosdem.org/2008/media/video 2008.*ogg --dump > urls


Spidering
^^^^^^^^^

Spider a site to depth ``3`` while pausing ``2`` seconds between fetches. The
urls that will be considered when spidering must match ``.*``:

.. code:: bash

    $ spiderfetch --host http://en.wikipedia.org --depth 3 --pause 2 '.*'
