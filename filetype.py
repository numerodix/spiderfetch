#!/usr/bin/env python

import re

import spider


# how many bytes of the file to download before doing a type check
HEADER_SIZE_HTML = 1024
HEADER_SIZE_URLS = 100*1024

# ref: file-4.23.tar.gz/magic/Magdir/sgml
html_regex = "(?ims).*<\s*(!DOCTYPE html|html|head|title|body)"
_html_re = re.compile(html_regex)

def is_html(data):
    if data and re.match(_html_re, data):
        return True

def has_urls(data, url):
    if data: 
        try:
            spider.findall(data, url).next()
            return True
        except StopIteration:
            pass

class WrongFileTypeError(Exception): pass



if __name__ == "__main__":
    import sys
    try:
        data = open(sys.argv[1], 'r').read()
        print "is_html:  %s" % is_html(data)
    except IndexError:
        print "Usage:  %s <url>" % sys.argv[0]
