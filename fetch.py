#!/usr/bin/env python

import ftplib
import httplib
import os
import socket
import tempfile
import time
import urllib

import filetype
import shcolor


""" testurls
http://video.fosdem.org/2008/maintracks/FOSDEM2008-cmake.ogg
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/livecd/livecd-i686-installer-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/installcd/install-x86-minimal-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/stages/stage1-x86-2007.0.tar.bz2
"""

# this should open some doors for us (IE7/Vista)
user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)"

# don't wait forever
socket.setdefaulttimeout(10)


class ErrorAlreadyProcessed(Exception): pass

class MyURLopener(urllib.URLopener):
    version = user_agent
    def __init__(self, fetcher):
        urllib.URLopener.__init__(self)
        self.fetcher = fetcher
    
#    def http_error_default(self, url, fp, errcode, errmsg, headers):
#        self.fetcher.write_progress(error=str(errcode))
#        raise ErrorAlreadyProcessed

class Fetcher(object):
    def __init__(self):
        self.action = None
        self.filename = None
        self.url = None
        self.typechecked = None
        self.timestamp = None
        self.totalsize = None

        self.linewidth = 78
        self.actionwidth = 6
        self.ratewidth = 10
        self.sizewidth = 10
        self.units = { 0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB", 5: "PB"}

        urllib._urlopener = MyURLopener(self)

    def write(self, s):
        sys.stdout.write(s)
        sys.stdout.flush()

    def truncate_url(self, width, s):
        radius = (len(s) - width + 4) / 2
        if radius > 0:
            mid = len(s) / 2
            s = s[0:mid-radius] + ".." + s[mid+radius:]
        return s

    def format_size(self, rate):
        c = 0
        while rate > 1000:
            rate = rate / 1024.
            c += 1
        r = "%3.1f" % rate
        u = "%s" % self.units[c]
        return r.rjust(5) + " " + u.ljust(2)

    def write_progress(self, rate=None, cursize=None, complete=False, error=None):
        # compute string lengths
        action = self.action.rjust(self.actionwidth)

        if error:
            rate = error
        elif complete:
            rate = "done"
        else:
            rate = "%s/s" % self.format_size(rate)
        rate = rate.ljust(self.ratewidth)

        if self.totalsize:
            size = self.format_size(self.totalsize)
        elif cursize:
            size = self.format_size(cursize)
        else:
            size = "????? B"
        size = (" %s" % size).ljust(self.sizewidth)

        line = "%s ::  %s  " % (action, rate)
        url_w = self.linewidth - len(line) - self.sizewidth
        url = self.truncate_url(url_w, self.url).ljust(url_w)

        # add formatting
        if error:
            rate = shcolor.color(shcolor.RED, rate)
        elif complete:
            rate = shcolor.color(shcolor.GREEN, rate)
        else:
            rate = shcolor.color(shcolor.YELLOW, rate)

        # draw progress bar
        if not (error or complete) and self.totalsize:
            c = int(url_w * cursize / self.totalsize)
            url = (shcolor.code(None, reverse=True) + url[:c] + 
                   shcolor.code(None) + url[c:])

        if not self.totalsize:
            size = shcolor.color(shcolor.YELLOW, size)

        line = "%s ::  %s  " % (action, rate)

        term = "\r"
        if error or complete: 
            term = "\n"
        self.write("%s%s%s%s" % (line, url, size, term))

    def fetch_hook(self, blocknum, blocksize, totalsize):
        step = 15
        if blocknum % step == 0:
            t = time.time()
            interval = t - self.timestamp
            self.timestamp = t

            rate = step * blocksize / interval
            cursize = blocknum * blocksize
            if totalsize and totalsize > 0:
                self.totalsize = totalsize
            self.write_progress(rate=rate, cursize=cursize)

        if not self.typechecked and blocknum*blocksize >= filetype.HEADER_SIZE:
            f = open(self.filename, 'r')
            data = f.read()
            f.close()
            if not filetype.is_html(data):
                raise filetype.WrongFileTypeError
            self.typechecked = True

    def load(self, url, filename=None):
        self.filename = filename
        self.url = url
        self.timestamp = time.time()

        if not self.filename:
            (_, self.filename) = tempfile.mkstemp()

        """This demonstrates getting the filetype from the HTTP header, which
        is available in the field Content-Type. However, this field is only
        present with HTTP and urllib uses mime types to guess filetypes of all
        other protocols (FTP, file:// etc), which is complete guesswork.

        urlobj = urllib.urlopen(url)
        self.type = urlobj.info().type
        """

        try:
            urllib.urlretrieve(url, filename=self.filename, 
                reporthook=self.fetch_hook)
            self.write_progress(complete=True)
        except filetype.WrongFileTypeError:
            os.unlink(self.filename)
            raise
        except ErrorAlreadyProcessed:
            return
        except IOError, exc:
            if exc and exc.args: 
                print exc.args
                if len(exc.args) == 2:
                    (_, errobj) = exc.args
                    if type(errobj) == socket.gaierror:
                        self.write_progress(error="dns")
                        return
                    elif type(errobj) == socket.error:
                        self.write_progress(error="socket")
                        return
                    elif type(errobj) == ftplib.error_perm:
                        self.write_progress(error="auth")
                        return
            raise

        return self.filename

    def fetch(self, url, filename):
        self.action = "fetch"
        self.typechecked = True
        self.load(url, filename=filename)

    def spider(self, url):
        self.action = "spider"
        self.load(url)

_fetcher = Fetcher()
fetch = _fetcher.fetch
spider = _fetcher.spider


if __name__ == "__main__":
    import sys
    try:
        fetch(sys.argv[2], sys.argv[1])
        #spider(sys.argv[1])
    except IndexError:
        print "Usage:  %s <url>" % sys.argv[0]
