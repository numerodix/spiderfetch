#!/usr/bin/env python

import os
import sys

import fetch
import filetype
import spider
import urlrewrite

url = sys.argv[1]


filename = fetch.spider(url)
data = open(filename, 'r').read()
os.unlink(filename)

urls = spider.unbox_it_to_ss(spider.findall(data))
urls = urlrewrite.rewrite_urls(url, urls)

for u in urls: 
    try:
        f = fetch.spider(u)
        os.unlink(f)
    except KeyboardInterrupt:
        fetch.write_abort()
        sys.exit(1)
    except:
        pass
        #print "url failed:", u
