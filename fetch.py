#!/usr/bin/env python

import ftplib
import httplib
import mimetools
import optparse
import os
import socket
import sys
import time
import urllib
import urlparse

import filetype
import io
import shcolor
import urlrewrite


""" testurls
http://video.fosdem.org/2008/maintracks/FOSDEM2008-cmake.ogg
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/livecd/livecd-i686-installer-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/installcd/install-x86-minimal-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/stages/stage1-x86-2007.0.tar.bz2
http://fc02.deviantart.com/fs11/i/2006/171/b/1/atomic_by_numerodix.jpg
"""

# this should open some doors for us (IE7/Vista)
user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)"

# don't wait forever
socket.setdefaulttimeout(10)


class ErrorAlreadyProcessed(Exception): pass
class ZeroDataError(Exception): pass
class DuplicateUrlWarning(Exception): pass
class UrlRedirectsOffHost(Exception): pass
class ChangedUrlWarning(Exception):
    def __init__(self, new_url):
        self.new_url = new_url


class MyURLopener(urllib.FancyURLopener):
    version = user_agent
    def __init__(self, fetcher):
        urllib.FancyURLopener.__init__(self)
        self.fetcher = fetcher
    
    def http_error_default(self, url, fp, errcode, errmsg, headers):
        self.fetcher.write_progress(error=str(errcode))
        raise ErrorAlreadyProcessed

    def prompt_user_passwd(self, host, realm):
        """Don't prompt for credentials"""
        return None, None

    def redirect_internal(self, url, fp, errcode, errmsg, headers, data):
        if 'location' in headers:
            newurl = headers['location']
        elif 'uri' in headers:
            newurl = headers['uri']
        #newurl = urlparse.urljoin(url, newurl)
        newurl = urlparse.urljoin(self.fetcher.url, newurl)
        raise ChangedUrlWarning(newurl)

class Fetcher(object):
    def __init__(self):
        self.action = None
        self.filename = None
        self.url = None
        self.timestamp = None
        self.download_size = None
        self.totalsize = None

        self.is_typechecked = None
        self.fetch_if_wrongtype = False

        self.linewidth = 78
        self.actionwidth = 6
        self.ratewidth = 10
        self.sizewidth = 10
        self.units = { 0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB", 5: "PB", 6: "EB"}

        urllib._urlopener = MyURLopener(self)

    def log_url(self, status, error=False):
        status = status.replace(" ", "_")
        actual = self.format_size(self.download_size).rjust(8)
        given = self.format_size(self.totalsize).rjust(8)
        line = "%s  %s  %s  %s\n" % (status.ljust(10), actual, given, self.url)
        if error:
            io.savelog(line, "error_urls", "a")
        else:
            io.savelog(line, "log_urls", "a")

    def truncate_url(self, width, s):
        radius = (len(s) - width + 3) / 2
        if radius > 0:
            mid = len(s) / 2
            s = s[0:mid-radius] + ".." + s[mid+radius:]
        return s

    def format_size(self, size):
        if size == None:
            size = -1

        c = 0
        while size > 1000:
            size = size / 1024.
            c += 1
        r = "%3.1f" % size
        u = "%s" % self.units[c]
        return r.rjust(5) + " " + u.ljust(2)

    def write_progress(self, rate=None, prestart=None, complete=False, error=None):
        # compute string lengths
        action = self.action.rjust(self.actionwidth)

        if error:
            rate = error
        elif prestart:
            rate = "starting"
        elif complete:
            rate = "done"
        else:
            rate = "%s/s" % self.format_size(rate)
        rate = rate.ljust(self.ratewidth)

        if self.totalsize:
            size = self.format_size(self.totalsize)
        elif self.download_size:
            size = self.format_size(self.download_size)
        else:
            size = "????? B"
        size = ("  %s" % size).ljust(self.sizewidth)

        line = "%s ::  %s  " % (action, rate)
        url_w = self.linewidth - len(line) - self.sizewidth
        url = self.truncate_url(url_w, self.url).ljust(url_w)

        # add formatting
        if error:
            rate = shcolor.color(shcolor.RED, rate)
        elif prestart:
            rate = shcolor.color(shcolor.CYAN, rate)
        elif complete:
            rate = shcolor.color(shcolor.GREEN, rate)
        else:
            rate = shcolor.color(shcolor.YELLOW, rate)

        # draw progress bar
        if not (error or prestart or complete) and self.totalsize:
            c = int(url_w * self.download_size / self.totalsize)
            url = shcolor.wrap_s(url, c, None, reverse=True)

        if not self.totalsize:
            size = shcolor.color(shcolor.YELLOW, size)

        line = "%s ::  %s  " % (action, rate)

        term = "\r"
        if error or complete: 
            term = "\n"
        io.write_err("%s%s%s%s" % (line, url, size, term))

        # log download
        if error:
            self.log_url(error, error=True)
        elif complete:
            self.log_url("done")

    def typecheck_html(self, filename):
        if not self.is_typechecked:
            data = open(self.filename, 'r').read()
            if data:
                if filetype.is_html(data):
                    self.is_typechecked = True

    def typecheck_urls(self, filename):
        if not self.is_typechecked:
            data = open(self.filename, 'r').read()
            if data:
                if not filetype.has_urls(data):
                    self.throw_type_error()
                self.is_typechecked = True

    def throw_type_error(self):
        if self.fetch_if_wrongtype:
            self.action = "fetch"
        else:
            raise filetype.WrongFileTypeError

    def fetch_hook(self, blocknum, blocksize, totalsize):
        self.download_size = blocknum * blocksize

        step = 12
        if blocknum % step == 0:
            t = time.time()
            interval = t - self.timestamp
            self.timestamp = t

            rate = step * blocksize / interval
            if totalsize and totalsize > 0:
                self.totalsize = totalsize
            self.write_progress(rate=rate)

        if not self.is_typechecked:
            if self.download_size >= filetype.HEADER_SIZE_HTML:
                self.typecheck_html(self.filename)
            if self.download_size >= filetype.HEADER_SIZE_URLS:
                self.typecheck_urls(self.filename)

    def load(self, url, filename):
        self.filename = filename
        self.url = url
        self.timestamp = time.time()

        """This demonstrates getting the filetype from the HTTP header, which
        is available in the field Content-Type. However, this field is only
        present with HTTP and urllib uses mime types to guess filetypes of all
        other protocols (FTP, file:// etc), which is complete guesswork.

        urlobj = urllib.urlopen(url)
        self.type = urlobj.info().type
        """

        try:
            self.write_progress(prestart=True)

            (_, headers) = urllib.urlretrieve(url, filename=self.filename, 
                reporthook=self.fetch_hook)
            
            self.download_size = os.path.getsize(self.filename)

            if isinstance(headers, mimetools.Message) and headers.fp \
               and not headers.fp.read(1):
                raise ZeroDataError

            if not self.is_typechecked:
                self.typecheck_html(self.filename)
            if not self.is_typechecked:
                self.typecheck_urls(self.filename)

            self.write_progress(complete=True)
        except filetype.WrongFileTypeError:
            self.write_progress(error="wrong type")
        except ZeroDataError:
            self.write_progress(error="no data")
        except urllib.ContentTooShortError:
            self.write_progress(error="incomplete")
        except ErrorAlreadyProcessed:
            pass
        except IOError, exc:
            if exc and exc.args: 
                if len(exc.args) == 2:
                    (_, errobj) = exc.args
                    if type(errobj) == socket.gaierror:
                        self.write_progress(error="dns")
                        return
                    elif type(errobj) == socket.timeout:
                        self.write_progress(error="timeout")
                        return
                    elif type(errobj) == socket.sslerror:
                        self.write_progress(error="ssl")
                        return
                    elif type(errobj) == socket.error:
                        self.write_progress(error="socket")
                        return
                    elif type(errobj) == ftplib.error_perm:
                        self.write_progress(error="auth")
                        return
            self.write_progress(error="url error")
            raise
        except socket.timeout:
            self.write_progress(error="timeout")
        except KeyboardInterrupt:
            io.write_abort()
            raise

    def spider(self, url, filename):
        self.action = "spider"
        self.is_typechecked = False
        self.fetch_if_wrongtype = False
        self.load(url, filename)

    def spider_fetch(self, url, filename):
        self.action = "spider"
        self.is_typechecked = False
        self.fetch_if_wrongtype = True
        self.load(url, filename)

    def fetch(self, url, filename):
        self.action = "fetch"
        self.is_typechecked = True
        self.fetch_if_wrongtype = False
        self.load(url, filename)

_fetcher = Fetcher()
spider = _fetcher.spider
spider_fetch = _fetcher.spider_fetch
fetch = _fetcher.fetch


if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "<url> [<file>] [options]"
    a("--spidertest", action="store_true", help="Test spider with url")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    (opts, args) = parser.parse_args()
    try:
        urllib._urlopener = urllib.FancyURLopener()
        url = args[0]
        if opts.spidertest:
            (fp, filename) = io.get_tempfile()
            spider(url, filename)
            os.close(fp) ; os.unlink(filename)
        else:
            if len(args) > 1:
                filename = args[1]
            else:
                filename = urlrewrite.url_to_filename(url)
            fetch(url, filename)
    except filetype.WrongFileTypeError:
        os.unlink(filename)
    except KeyboardInterrupt:
        sys.exit()
    except IndexError:
        io.opts_help(None, None, None, parser)
