#!/usr/bin/env python

import re


# how many bytes of the file to download before doing a type check
HEADER_SIZE = 1024

# ref: file-4.23.tar.gz/magic/Magdir/sgml
html_regex = "(?ims).*<\s*(!DOCTYPE html|html|head|title|body)"
_html_re = re.compile(html_regex)

def is_html(data):
    if re.match(_html_re, data):
        return True

class WrongFileTypeError(Exception): pass



if __name__ == "__main__":
    import sys
    try:
        f = open(sys.argv[1], 'r')
        data = f.read()
        print "is_html:  %s" % is_html(data)
    except IndexError:
        print "Usage:  %s <url>" % sys.argv[0]
