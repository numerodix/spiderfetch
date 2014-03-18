#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import re
import urllib

import ansicolor

from spiderfetch import ioutils
from spiderfetch import urlrewrite


testcases = """\
<a href="http://1host/path">
<a href="http://2host/path" >
<a href='http://3host/path' >
<a href'http://4host/path' >
< href"http://5host/path" >
< href=http://6host/path >
<a href=`http://7host/path`>
<a href="http://8host/p\"ath">
<a href="http://9host/path"att">
<a href="http://10host/p'ath">
<a href="http://11
host/path">
<a href="http://12
 host/path">
<a href=13file.path>
<a href= 14file.pat h >
"""

_link = """(?ims)<\s*a[^>]+href[ ]*=?[ ]*(?P<quot>["'`])(?P<url>.*?)(?P=quot)[^>]*?>"""
LINK = re.compile(_link)

_link_unq = """(?ims)<\s*a[^>]+href=[ ]*(?P<url>[^'">]+?)[ ]*>"""
LINK_UNQ = re.compile(_link_unq)

_frame = """(?ims)<\s*i?frame[^>]+src[ ]*=?[ ]*(?P<quot>["'`])(?P<url>.*?)(?P=quot)[^>]*?>"""
FRAME = re.compile(_frame)

_frame_unq = """(?ims)<\s*i?frame[^>]+src=[ ]*(?P<url>[^'">]+?)[ ]*>"""
FRAME_UNQ = re.compile(_frame_unq)

_img = """(?ims)<\s*img[^>]+src[ ]*=?[ ]*(?P<quot>["'`])(?P<url>.*?)(?P=quot)[^>]*?>"""
IMG = re.compile(_img)

_img_unq = """(?ims)<\s*img[^>]+src=[ ]*(?P<url>[^'">]+?)[ ]*?>"""
IMG_UNQ = re.compile(_img_unq)

_uri_match = """(?ims)(?P<url>[a-z][a-z0-9+.-]{1,120}:\/\/(([a-z0-9$_.+!*,;\/?:@&~(){}\[\]=-])|%[a-f0-9]{2}){1,333}([a-z0-9][a-z0-9 $_.+!*,;\/?:@&~(){}\[\]=%-]{0,1000})?)"""
URI_MATCH = re.compile(_uri_match)

#-rw-r--r--    1 1042     1042     28620269 Apr 19  2007 stage1-x86-2007.0.tar.bz2
_ftp_listing = """.[^ ]{9}(?:\s+[^ ]+){7}\s+(?P<url>.*)$"""
FTP_LISTING = re.compile(_ftp_listing)


def find_with_r(r, s):
    return re.finditer(r, s)

def spider_ftp(s):
    lines = s.splitlines()
    filler = ""
    for line in lines:
        it = re.finditer(FTP_LISTING, filler + line)
        filler += (2 + len(line)) * " "
        for match in it:
            yield match

def spider(s):
    for it in [find_with_r(r, s) for r in (LINK, LINK_UNQ, FRAME, FRAME_UNQ, IMG, IMG_UNQ)]:
        for match in it:
            yield match

def harvest(s):
    return find_with_r(URI_MATCH, s)

def findall(s, url=None):
    its = [spider(s), harvest(s)]
    if url and urlrewrite.get_scheme(url) == "ftp":
        its.append(spider_ftp(s))
    for (idx, it) in enumerate(its):
        for match in it:
            yield match

def unbox_it_to_ss(it):
    for match in it:
        yield match.group('url')

def group_by_regex(s, url=None):
    its = [spider(s), harvest(s)]
    if url and urlrewrite.get_scheme(url) == "ftp":
        its.append(spider_ftp(s))
    for (idx, it) in enumerate(its):
        for match in it:
            yield (idx, match)

def unique(it):
    seen = set()
    return [x for x in it if x not in seen and not seen.add(x)]

def colorize_shell(str, url=None):
    it = group_by_regex(str, url)

    # split iterator of (rx_id, match) into lists by rx_id
    regexs = {}
    for rx in it:
        (rx_id, match) = rx
        try:
            regexs[rx_id].append(match)
        except KeyError:
            regexs[rx_id] = []
            regexs[rx_id].append(match)

    spanlists = [map(lambda m: m.span('url'), regexs[rx_id])
                 for rx_id in sorted(regexs.keys())]
    return ansicolor.highlight_string(str, *spanlists)



if __name__ == "__main__":
    (parser, a) = ioutils.init_opts("[ <url|file> [options] | --test ]")
    a("--dump", action="store_true", help="Dump urls")
    a("--test", action="store_true", help="Run spider testsuite")
    (opts, args) = ioutils.parse_args(parser)
    try:
        url = None
        if opts.test:
            data = testcases
        else:
            url = args[0]
            data = urllib.urlopen(url).read()

        if opts.dump:
            for u in unique(unbox_it_to_ss(findall(data, url))):
                print(u)
        else:
            print(colorize_shell(data, url))
    except IndexError:
        ioutils.opts_help(None, None, None, parser)
