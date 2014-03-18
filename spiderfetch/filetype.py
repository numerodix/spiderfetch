#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import re
import sys

from spiderfetch import spider


# how many bytes of the file to download before doing a type check
HEADER_SIZE_HTML = 1024
HEADER_SIZE_URLS = 100 * 1024

# ref: file-4.23.tar.gz/magic/Magdir/sgml
html_regex = "(?ims).*<\s*(!DOCTYPE html|html|head|title|body)"
_html_re = re.compile(html_regex)

class WrongFileTypeError(Exception):
    pass


def is_html(data):
    if data and re.match(_html_re, data):
        return True

def has_urls(data, url=None):
    if data:
        try:
            next(spider.findall(data, url))
            return True
        except StopIteration:
            pass



if __name__ == "__main__":
    try:
        data = open(sys.argv[1], 'r').read()
        print("is_html:  %s" % is_html(data))
        print("has_urls: %s" % has_urls(data))
    except IndexError:
        print("Usage:  %s <url>" % sys.argv[0])
