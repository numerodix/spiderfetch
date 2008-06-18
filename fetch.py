#!/usr/bin/env python

import tempfile
import urllib

import filetype


""" testurls
http://video.fosdem.org/2008/maintracks/FOSDEM2008-cmake.ogg
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/livecd/livecd-i686-installer-2007.0.iso
"""

# this should open some doors for us (IE7/Vista)
user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)"


class Fetcher(object):
    def __init__(self):
        self.filename = None
        self.url = None

        class MyURLopener(urllib.FancyURLopener):
            version = user_agent
        urllib._urlopener = MyURLopener()

    def fetch_hook(self, blocknum, blocksize, totalsize):
        print blocknum*blocksize, totalsize, '\t', self.url
        if blocknum*blocksize >= filetype.HEADER_SIZE:
            f = open(self.filename, 'r')
            data = f.read()
            f.close()
            if not filetype.is_html(data):
                raise filetype.WrongFileTypeError

    def load(self, url, filename=None):
        self.filename = filename
        self.url = url

        if not self.filename:
            (_, self.filename) = tempfile.mkstemp()

        """This demonstrates getting the filetype from the HTTP header, which
        is available in the field Content-Type. However, this field is only
        present with HTTP and urllib uses mime types to guess filetypes of all
        other protocols (FTP, file:// etc), which is complete guesswork.

        urlobj = urllib.urlopen(url)
        self.type = urlobj.info().type
        """

        urllib.urlretrieve(url, filename=self.filename, reporthook=self.fetch_hook)
        # XXX catch exception to unlink tempfile

_fetcher = Fetcher()
load = _fetcher.load


if __name__ == "__main__":
    import sys
    try:
        load(sys.argv[1])
    except IndexError:
        print "Usage:  %s <url>" % sys.argv[0]
