#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import ftplib
import os
import re
import socket
import sys
import time
import urllib

import ansicolor

from spiderfetch import filetype
from spiderfetch import ioutils
from spiderfetch import urlrewrite
from spiderfetch.compat import ContentTooShortError
from spiderfetch.compat import FancyURLopener
from spiderfetch.compat import ftpwrapper
from spiderfetch.compat import splittype
from spiderfetch.compat import unwrap
from spiderfetch.compat import urlparse


""" testurls
http://video.fosdem.org/2008/maintracks/FOSDEM2008-cmake.ogg
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/livecd/livecd-i686-installer-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/installcd/install-x86-minimal-2007.0.iso
ftp://ftp.linux.ee/pub/gentoo/distfiles/releases/x86/2007.0/stages/stage1-x86-2007.0.tar.bz2
http://fc02.deviantart.com/fs11/i/2006/171/b/1/atomic_by_numerodix.jpg
"""

# this should open some doors for us (IE7/Vista)
_user_agent = "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)"
if os.environ.get('VANILLA_USER_AGENT'):
    _user_agent = "spiderfetch"

# don't wait forever
timeout = 10
if os.environ.get("SOCKET_TIMEOUT"):
    timeout = int(os.environ.get("SOCKET_TIMEOUT"))
socket.setdefaulttimeout(timeout)

# log downloads
os.environ["LOGGING"] = str(True)

CHECKSUM_SIZE = 10 * 1024

RETRY_WAIT = 10

class ErrorAlreadyProcessed(Exception):
    pass

class ZeroDataError(Exception):
    pass

class DuplicateUrlWarning(Exception):
    pass

class UrlRedirectsOffHost(Exception):
    pass

class ResumeChecksumFailed(Exception):
    pass

class ResumeNotSupported(Exception):
    pass

class ChangedUrlWarning(Exception):
    def __init__(self, new_url):
        self.new_url = new_url

class err(object):
    def __init__(self):
        self.dns = 1
        self.timeout = 2
        self.socket = 3
        self.ssl = 4
        self.auth = 5
        self.url_error = 6
        self.incomplete = 7
        self.wrong_type = 8
        self.no_data = 9
        self.redirect = 10
        self.checksum = 11
        self.no_resume = 12

        self.temporal = [self.timeout, self.socket, self.url_error, self.http_503]

    def __getattr__(self, att):
        """Disclaimer: Hackish
        We accept lookup on any error declared in class definition, as well as
        anything that matches 'ftp|http_[0-9]{3}'. Once found, we stick it in
        the dict so that it can be found by str()."""
        try:
            return self.__dict__[att]
        except KeyError:
            m = re.search("^(ftp|http)_([0-9]{3})$", att)
            if m and m.groups():
                if m.group(1) == "ftp":
                    val = 1000 + int(m.group(2))
                if m.group(1) == "http":
                    val = 2000 + int(m.group(2))
                setattr(self, att, val)
                return val
            raise AttributeError

    def str(self, att):
        """Look up the name of an error in the object dict"""
        for (k, v) in self.__dict__.items():
            if att == v:
                return k.replace("_", " ")
        raise AttributeError

    def is_temporal(self, e):
        """Some errors are temporal, retrying the fetch later could work"""
        if e in self.temporal:
            return True

err = err()     # XXX ugly, but it's messy enough to do this on an instance

# Override ftpwrapper from urllib to change ntransfercmd call, now using 'rest'
class Myftpwrapper(ftpwrapper):
    def retrfile(self, file, type, rest=None):
        import ftplib  # noqa
        self.endtransfer()
        if type in ('d', 'D'):
            cmd = 'TYPE A'
            isdir = 1
        else:
            cmd = 'TYPE ' + type
            isdir = 0
        try:
            self.ftp.voidcmd(cmd)
        except ftplib.all_errors:
            self.init()
            self.ftp.voidcmd(cmd)
        conn = None
        if file and not isdir:
            # Try to retrieve as a file
            try:
                cmd = 'RETR ' + file
                conn = self.ftp.ntransfercmd(cmd, rest=rest)
            except ftplib.error_perm as reason:
                if str(reason)[:3] != '550':
                    raise IOError(('ftp error', reason), sys.exc_info()[2])
        if not conn:
            # Set transfer mode to ASCII!
            self.ftp.voidcmd('TYPE A')
            # Try a directory listing
            if file:
                cmd = 'LIST ' + file
            else:
                cmd = 'LIST'
            conn = self.ftp.ntransfercmd(cmd)
        self.busy = 1
        # Pass back both a suitably decorated object and a retrieval length
        return (urllib.addclosehook(conn[0].makefile('rb'),
                                    self.endtransfer), conn[1])

class MyURLopener(FancyURLopener):
    checksum_size = CHECKSUM_SIZE
    version = _user_agent

    def __init__(self, fetcher):
        FancyURLopener.__init__(self)
        self.fetcher = fetcher

    def prompt_user_passwd(self, host, realm):
        """Don't prompt for credentials"""
        return None, None

    def http_error_default(self, url, fp, errcode, errmsg, headers):
        if os.environ.get("SILENT_REDIRECT"):
            return urllib.FancyURLopener.http_error_default(
                self, url, fp, errcode, errmsg, headers)

        self.fetcher.handle_error(eval('err.http_' + str(errcode)))
        raise ErrorAlreadyProcessed

    def redirect_internal(self, url, fp, errcode, errmsg, headers, data):
        if os.environ.get("SILENT_REDIRECT"):
            return urllib.FancyURLopener.redirect_internal(
                self, url, fp, errcode, errmsg, headers, data)

        if 'location' in headers:
            newurl = headers['location']
        elif 'uri' in headers:
            newurl = headers['uri']
        #newurl = urlparse.urljoin(url, newurl)
        newurl = urlparse.urljoin(self.fetcher.url, newurl)
        raise ChangedUrlWarning(newurl)

    def set_header(self, pair):
        (key, value) = pair
        found = False
        for (i, (k, v)) in enumerate(self.addheaders):
            if key == k:
                found = True
                self.addheaders[i] = pair
        if not found:
            self.addheaders.append(pair)

    def continue_file(self, filename):
        localsize = os.path.getsize(filename)
        if localsize < self.checksum_size:
            self.checksum_size = localsize
        seekto = localsize - self.checksum_size

        # set var read in open_ftp()
        os.environ["REST"] = str(seekto)

        # set header for http
        self.set_header(('Range', 'bytes=%s-' % seekto))

        return localsize

    # Override function from urllib to support resuming transfers
    def retrieve(self, url, filename, reporthook=None, data=None, cont=None):
        """retrieve(url) returns (filename, headers) for a local object
        or (tempfilename, headers) for a remote object."""
        url = unwrap(url)
        if self.tempcache and url in self.tempcache:
            return self.tempcache[url]
        type, url1 = splittype(url)
        if filename is None and (not type or type == 'file'):
            try:
                fp = self.open_local_file(url1)
                hdrs = fp.info()
                del fp
                return urllib.url2pathname(urllib.splithost(url1)[1]), hdrs
            except IOError:
                pass
        bs = 1024 * 8
        size = -1
        read = 0
        blocknum = 0
        if cont:
            localsize = self.continue_file(filename)
            read = localsize
            blocknum = localsize / bs
        fp = self.open(url, data)
        headers = fp.info()
        if cont:
            if (self.fetcher.proto == self.fetcher.PROTO_HTTP and
                not (headers.dict.get("content-range") or
                     headers.dict.get("Content-Range"))):
                raise ResumeNotSupported
            tfp = open(filename, 'rb+')
            tfp.seek(-self.checksum_size, os.SEEK_END)
            local = tfp.read(self.checksum_size)
            remote = fp.read(self.checksum_size)
            if not local == remote:
                raise ResumeChecksumFailed
        else:
            tfp = open(filename, 'wb')
        result = filename, headers
        if self.tempcache is not None:
            self.tempcache[url] = result
        if reporthook:
            if "content-length" in headers:
                size = int(headers["Content-Length"])
                if cont and self.fetcher.proto == self.fetcher.PROTO_HTTP:
                    size = size + localsize - self.checksum_size
            reporthook(blocknum, bs, size)
        while 1:
            block = fp.read(bs)
            if not block:
                break
            read += len(block)
            tfp.write(block)
            blocknum += 1
            if reporthook:
                reporthook(blocknum, bs, size)
        fp.close()
        tfp.close()
        del fp
        del tfp

        # raise exception if actual size does not match content-length header
        if size >= 0 and read < size:
            raise ContentTooShortError("retrieval incomplete: got only %i out "
                                       "of %i bytes" % (read, size), result)

        return result

    # Override function from urllib to use custom frpwrapper
    def open_ftp(self, url):
        """Use FTP protocol."""
        if not isinstance(url, str):
            raise IOError(('ftp error', 'proxy support for ftp protocol currently not implemented'))
        import mimetypes
        import mimetools
        try:
            from cStringIO import StringIO
        except ImportError:
            from StringIO import StringIO
        host, path = urllib.splithost(url)
        if not host:
            raise IOError(('ftp error', 'no host given'))
        host, port = urllib.splitport(host)
        user, host = urllib.splituser(host)
        if user:
            user, passwd = urllib.splitpasswd(user)
        else:
            passwd = None
        host = urllib.unquote(host)
        user = urllib.unquote(user or '')
        passwd = urllib.unquote(passwd or '')
        host = socket.gethostbyname(host)
        if not port:
            import ftplib  # noqa
            port = ftplib.FTP_PORT
        else:
            port = int(port)
        path, attrs = urllib.splitattr(path)
        path = urllib.unquote(path)
        dirs = path.split('/')
        dirs, file = dirs[:-1], dirs[-1]
        if dirs and not dirs[0]:
            dirs = dirs[1:]
        if dirs and not dirs[0]:
            dirs[0] = '/'
        key = user, host, port, '/'.join(dirs)
        # XXX thread unsafe!
        if len(self.ftpcache) > urllib.MAXFTPCACHE:
            # Prune the cache, rather arbitrarily
            for k in self.ftpcache.keys():
                if k != key:
                    v = self.ftpcache[k]
                    del self.ftpcache[k]
                    v.close()
        try:
            if not key in self.ftpcache:
                self.ftpcache[key] = \
                    Myftpwrapper(user, passwd, host, port, dirs)
            if not file:
                type = 'D'
            else:
                type = 'I'
            for attr in attrs:
                attr, value = urllib.splitvalue(attr)
                if attr.lower() == 'type' and \
                   value in ('a', 'A', 'i', 'I', 'd', 'D'):
                    type = value.upper()
            (fp, retrlen) = self.ftpcache[key].retrfile(file, type,
                                                        rest=os.environ.get("REST"))
            mtype = mimetypes.guess_type("ftp:" + url)[0]
            headers = ""
            if mtype:
                headers += "Content-Type: %s\n" % mtype
            if retrlen is not None and retrlen >= 0:
                headers += "Content-Length: %d\n" % retrlen
            headers = mimetools.Message(StringIO(headers))
            return urllib.addinfourl(fp, headers, "ftp:" + url)
        except urllib.ftperrors() as msg:
            raise IOError(('ftp error', msg), sys.exc_info()[2])

class Fetcher(object):
    FETCH = 1
    SPIDER = 2
    SPIDER_FETCH = 3

    PROTO_FTP = 1
    PROTO_HTTP = 2

    linewidth = 78
    actionwidth = 6
    ratewidth = 10
    sizewidth = 10
    urlwidth = linewidth - actionwidth - ratewidth - sizewidth - 7  # 7 for spaces
    units = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB", 5: "PB", 6: "EB"}

    def __init__(self, mode=FETCH, url=None, filename=None):
        self._opener = MyURLopener(self)
        urllib._urlopener = self._opener

        self.is_typechecked = False
        self.fetch_if_wrongtype = False
        self.mode = mode
        if mode == self.FETCH:
            self.action = "fetch"
            self.is_typechecked = True
        elif mode == self.SPIDER:
            self.action = "spider"
        elif mode == self.SPIDER_FETCH:
            self.action = "spider"
            self.fetch_if_wrongtype = True

        self.tries = 1
        if os.environ.get("TRIES"):
            self.tries = int(os.environ.get("TRIES"))
        self.retry_wait = RETRY_WAIT

        self.proto = None
        self.url = url
        self.filename = filename

        self.timestamp = None
        self.download_size = None
        self.totalsize = None

        self.started = False
        self.error = None

    def set_referer(self, url):
        """Some hosts block requests from referers off-site"""
        self._opener.set_header(('Referer', urlrewrite.get_referer(url)))

    def get_url(self):
        return self._url

    def set_url(self, url):
        self._url = url
        self.url_fmt = urlrewrite.truncate_url(self.urlwidth, url).ljust(self.urlwidth)
        proto = urlrewrite.get_scheme(url)
        if proto == "ftp":
            self.proto = self.PROTO_FTP
        elif proto == "http" or "https":
            self.proto = self.PROTO_HTTP
        self.set_referer(url)

    url = property(fget=get_url, fset=set_url)

    def handle_error(self, e):
        self.error = e
        self.write_progress(error=err.str(e))

    def log_url(self, status, error=False):
        status = status.replace(" ", "_")
        actual = self.format_size(self.download_size).rjust(8)
        given = self.format_size(self.totalsize).rjust(8)
        line = "%s  %s  %s  %s\n" % (status.ljust(10), actual, given, self.url)
        if not os.environ["LOGGING"] == str(False):
            if error:
                ioutils.savelog(line, "error_urls", "a")
            else:
                ioutils.savelog(line, "log_urls", "a")

    def format_size(self, size):
        if size is None:
            size = -1

        c = 0
        while size > 999:
            size = size / 1024.
            c += 1
        r = "%3.1f" % size
        u = "%s" % self.units[c]
        return r.rjust(5) + " " + u.ljust(2)

    def write_progress(self, rate=None, prestart=None, wait=None, complete=False, error=None):
        # compute string lengths
        action = self.action.rjust(self.actionwidth)

        if error:
            rate = error
        elif prestart:
            rate = "starting"
        elif wait:
            rate = ("%s" % self.retry_wait) + "s..."
        elif complete:
            rate = "done"
        else:
            rate = "%s/s" % self.format_size(rate)
        rate = rate.ljust(self.ratewidth)

        url = self.url_fmt

        if self.totalsize:
            size = self.format_size(self.totalsize)
        elif self.download_size:
            size = self.format_size(self.download_size)
        else:
            size = "????? B"
        size = ("  %s" % size).ljust(self.sizewidth)

        # add formatting
        if error:
            rate = ansicolor.red(rate)
        elif prestart or wait:
            rate = ansicolor.cyan(rate)
        elif complete:
            rate = ansicolor.green(rate)
        else:
            rate = ansicolor.yellow(rate)

        # draw progress bar
        if not (error or prestart or complete) and self.totalsize:
            c = int(self.urlwidth * self.download_size / self.totalsize)
            url = ansicolor.wrap_string(self.url_fmt, c, None, reverse=True)

        if not self.totalsize:
            size = ansicolor.yellow(size)

        line = "%s ::  %s  " % (action, rate)

        term = (os.environ.get("DEBUG_FETCH") and "\n") or "\r"
        if error or complete:
            term = "\n"
        ioutils.write_err("%s%s%s%s" % (line, url, size, term))

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
                if not filetype.has_urls(data, self.url):
                    self.throw_type_error()
                self.is_typechecked = True

    def throw_type_error(self):
        if self.fetch_if_wrongtype:
            self.action = "fetch"
        else:
            raise filetype.WrongFileTypeError

    def fetch_hook(self, blocknum, blocksize, totalsize):
        self.download_size = blocknum * blocksize

        step = 5
        if blocknum > 0 and blocknum % step == 0:
            t = time.time()
            interval = t - self.timestamp
            self.timestamp = t

            rate = step * blocksize / max(interval, 0.1)
            if totalsize and totalsize > 0:
                self.totalsize = totalsize
            self.write_progress(rate=rate)

        if not self.is_typechecked:
            if self.download_size >= filetype.HEADER_SIZE_HTML:
                self.typecheck_html(self.filename)
            if self.download_size >= filetype.HEADER_SIZE_URLS:
                self.typecheck_urls(self.filename)

    def inner_load_url(self):
        cont = False
        if not self.mode == self.SPIDER:
            if (os.environ.get("CONT") and os.path.exists(self.filename)
                    and os.path.getsize(self.filename) > 0):
                cont = True

        # init vars here as we might start fetching from a non-zero position
        self.timestamp = time.time()
        self.started = True

        (_, headers) = self._opener.retrieve(self.url, self.filename,
                                             reporthook=self.fetch_hook, cont=cont)


    def load_url(self):
        self.write_progress(prestart=True)

        self.inner_load_url()

        self.download_size = os.path.getsize(self.filename)
        if not self.download_size:
            raise ZeroDataError

        """This was a check to detect zero data transmissions, but it
        causes ftp indices to fail, so it may be worthless. Reading the
        filesize might be more useful.

        if isinstance(headers, mimetools.Message) and headers.fp \
           and not headers.fp.read(1):
            raise ZeroDataError
        """

        if not self.is_typechecked:
            self.typecheck_html(self.filename)
        if not self.is_typechecked:
            self.typecheck_urls(self.filename)

        self.write_progress(complete=True)

    def launch(self):

        """This demonstrates getting the filetype from the HTTP header, which
        is available in the field Content-Type. However, this field is only
        present with HTTP and urllib uses mime types to guess filetypes of all
        other protocols (FTP, file:// etc), which is complete guesswork.

        urlobj = urllib.urlopen(url)
        self.type = urlobj.info().type
        """

        try:
            # clear error
            self.error = None

            self.load_url()
        except ChangedUrlWarning:
            self.handle_error(err.redirect)
            raise
        except filetype.WrongFileTypeError:
            self.handle_error(err.wrong_type)
        except ZeroDataError:
            self.handle_error(err.no_data)
        except ContentTooShortError:
            self.handle_error(err.incomplete)
        except ResumeChecksumFailed:
            self.handle_error(err.checksum)
        except ResumeNotSupported:
            self.handle_error(err.no_resume)
        except ErrorAlreadyProcessed:
            pass
        except IOError as exc:
            if exc and exc.args:
                if len(exc.args) == 2:
                    (_, errobj) = exc.args
                    if type(errobj) == socket.gaierror:
                        self.handle_error(err.dns)
                        return
                    elif type(errobj) == socket.timeout:
                        self.handle_error(err.timeout)
                        return
                    elif type(errobj) == socket.sslerror:
                        self.handle_error(err.ssl)
                        return
                    elif type(errobj) == socket.error:
                        self.handle_error(err.socket)
                        return
                    elif type(errobj) == ftplib.error_perm:
                        self.handle_error(err.auth)
                        return
            self.handle_error(err.url_error)
        except socket.timeout:
            self.handle_error(err.timeout)
        except KeyboardInterrupt:
            ioutils.write_abort()
            raise

    def launch_w_tries(self):
        while True:
            self.tries -= 1

            self.launch()

            if not self.error or not err.is_temporal(self.error):
                return

            if self.tries < 1:
                return

            # retry after a short delay
            self.write_progress(wait=True)
            time.sleep(self.retry_wait)



if __name__ == "__main__":
    (parser, a) = ioutils.init_opts("<url>+ [options]")
    a("--fullpath", action="store_true",
      help="Use full path as filename to avoid name collisions")
    a("-c", "--continue", dest="cont", action="store_true", help="Resume downloads")
    a("-t", "--tries", dest="tries", type="int", action="store", help="Number of retries")
    a("-q", "--quiet", dest="quiet", action="store_true", help="Turn off logging")
    a("--spidertest", action="store_true", help="Test spider with url")
    (opts, args) = ioutils.parse_args(parser)
    if getattr(opts, 'cont', None):
        os.environ["CONT"] = "1"
    if getattr(opts, 'tries', None):
        if not os.environ.get("TRIES"):
            os.environ["TRIES"] = str(opts.tries)
    if opts.quiet:
        os.environ["LOGGING"] = str(False)
    try:
        url = args[0]
        os.environ["SILENT_REDIRECT"] = "1"
        if opts.spidertest:
            (fp, filename) = ioutils.get_tempfile()
            Fetcher(mode=Fetcher.SPIDER, url=url,
                    filename=filename).launch_w_tries()
            os.close(fp)
            os.unlink(filename)
        else:
            args = list(args)
            if len(args) <= 5:
                os.environ["LOGGING"] = str(False)
            args.reverse()
            os.environ["ORIG_FILENAMES"] = os.environ.get("ORIG_FILENAMES") or "1"
            if opts.fullpath:
                os.environ["ORIG_FILENAMES"] = "0"
            while args:
                url = args.pop()
                filename = urlrewrite.url_to_filename(url)
                if not os.environ.get("CONT"):
                    filename = ioutils.safe_filename(filename)
                try:
                    Fetcher(mode=Fetcher.FETCH, url=url,
                            filename=filename).launch_w_tries()
                except Exception as e:
                    print(e)
    except filetype.WrongFileTypeError:
        os.unlink(filename)
    except KeyboardInterrupt:
        sys.exit()
    except IndexError:
        ioutils.opts_help(None, None, None, parser)
