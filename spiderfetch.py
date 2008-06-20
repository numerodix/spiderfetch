#!/usr/bin/env python

import os
import sys

import fetch
import spider

url = sys.argv[1]


filename = fetch.spider(url)
data = open(filename, 'r').read()
os.unlink(filename)

urls = spider.unbox_it_to_ss(spider.spider(data))
for u in urls: print u
