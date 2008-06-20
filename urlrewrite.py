#!/usr/bin/env python

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

def rewrite_urls(origin_url, urls):
    for u in urls:
        pack = urlparse.urlsplit(u)
        (scheme, netloc, path, query, fragment) = pack

        # try to rewrite scheme
        scheme = rewrite_scheme(pack.scheme)

        new_u = urlparse.urlunsplit((scheme, netloc, path, query, None))

        # no scheme or netloc, it's a path on-site
        if not scheme and not netloc and path:
            path_query = urlparse.urlunsplit((None, None, path, query, None))
            new_u = urlparse.urljoin(origin_url, path_query)

        if new_u:
            yield new_u

        # XXX error handling


if __name__ == "__main__":
    base = "http://www.juventuz.com/forum/search.php?searchid=1186852"
    urls = ["../index.php?name=jack&act=whatever"]
    for u in rewrite_urls(base, urls):
        print u
