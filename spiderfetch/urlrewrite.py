#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

from functools import reduce
import os
import re

from spiderfetch.compat import urlparse


SCHEMES = ["ftp", "http", "https"]

_scheme = "(?P<scheme>%s)$" % "".join(reduce(lambda x, y: "%s|%s" % (x, y), SCHEMES))
scheme_regex = re.compile(_scheme)

class InvalidUrl(Exception):
    pass

def rewrite_scheme(scheme):
    m = re.search(scheme_regex, scheme)
    if m and m.groups():
        return m.group('scheme')
    return scheme

def assemble_netloc(username, password, hostname, port):
    netloc = hostname
    if username:
        if password:
            username = "%s:%s" % (username, password)
        netloc = "%s@%s" % (username, hostname)
    if port:
        netloc = "%s:%s" % (netloc, port)
    return netloc

def get_hostname(url):
    pack = urlparse.urlsplit(url)
    return pack.hostname

def get_scheme(url):
    pack = urlparse.urlsplit(url)
    return pack.scheme

def get_referer(url):
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    path = os.path.dirname(path)
    return urlparse.urlunsplit((scheme, netloc, path, None, None))

def truncate_url(width, s):
    if len(s) > width:
        filler = "..."
        w = width - len(filler)
        half = w // 2
        rest = w % 2
        s = s[:half + rest] + filler + s[-half:]
    return s

def rewrite_urls(origin_url, urls):
    origin_pack = urlparse.urlsplit(origin_url)
    for u in urls:
        # kill breaks
        if u:
            u = re.sub("(\n|\t)", "", u)

        pack = urlparse.urlsplit(u)
        (scheme, netloc, path, query, fragment) = pack

        # try to rewrite scheme
        scheme = rewrite_scheme(pack.scheme)

        # rewrite netloc to include credentials
        if origin_pack.username and pack.hostname == origin_pack.hostname:
            netloc = assemble_netloc(origin_pack.username,
                                     origin_pack.password, pack.hostname, pack.port)

        # reassemble into url
        new_u = urlparse.urlunsplit((scheme, netloc, path, query, None))

        # no scheme or netloc, it's a path on-site
        if not scheme and not netloc and (path or query):
            path_query = urlparse.urlunsplit(('', '', path, query, ''))
            new_u = urlparse.urljoin(origin_url, path_query)

        # quote spaces
        new_u = new_u.replace(" ", "%20")
        if new_u:
            yield new_u

        # drop null urls on the floor, eg: #chapter2

def url_to_filename(url):
    (scheme, netloc, path, query, _) = urlparse.urlsplit(url)
    file = os.path.basename(path)
    if os.environ.get("ORIG_FILENAMES") == "1" and file:
        filename = file
    else:
        (path, ext) = os.path.splitext(path)
        filename = "_".join([x for x in (scheme, netloc, path, query) if x])
        filename = re.sub("[^a-zA-Z0-9]", "_", filename)
        filename = re.sub("_{2,}", "_", filename)
        filename = re.sub("_$", "", filename)
        filename = filename + ext
    return filename

def hostname_to_filename(url):
    return re.sub("[^a-zA-Z0-9]", "_", url)



if __name__ == "__main__":
    base = "http://user:pass@www.juventuz.com/forum/search.php?searchid=1186852"
    urls = ["../index.php?name=jack&act=whatever",
            "http://www.juventuz.com/matches"]
    for u in rewrite_urls(base, urls):
        print(u)
