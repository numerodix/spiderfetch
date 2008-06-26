#!/usr/bin/env python

import os
import re
import urlparse

import spider


_scheme = "(?P<scheme>%s)$" % "".join(reduce(lambda x, y: "%s|%s" % (x, y), spider.SPIDER_SCHEMES))
scheme_regex = re.compile(_scheme)

class InvalidUrl(Exception): pass

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
            netloc = assemble_netloc(origin_pack.username,\
                        origin_pack.password, pack.hostname, pack.port)

        # reassemble into url
        new_u = urlparse.urlunsplit((scheme, netloc, path, query, None))

        # no scheme or netloc, it's a path on-site
        if not scheme and not netloc and (path or query):
            path_query = urlparse.urlunsplit((None, None, path, query, None))
            new_u = urlparse.urljoin(origin_url, path_query)

        # quote spaces
        new_u = new_u.replace(" ", "%20")
        if new_u:
            yield new_u

        # drop null urls on the floor, eg: #chapter2

def url_to_filename(url):
    (scheme, netloc, path, query, _) = urlparse.urlsplit(url)
    if os.environ.get("SHORT_FILENAMES"):
        filename = os.path.basename(path)
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
        print u
