#!/usr/bin/env python

import os
import pickle
import sys
import tempfile
import traceback

import fetch
import filetype
import recipe
import spider
import urlrewrite
import web


url = sys.argv[1]
web = web.Web()
web.add_url(url, [])

def write_out(self, s):
    sys.stdout.write(s)

def get_url_w_redirects(getter, url, filename):
    """http 30x redirects produce a recursion with new urls that may or may not
    have been seen before"""
    while True:
        try:
            getter(url, filename)
            break
        except fetch.ChangedUrlWarning, e:
            if e.new_url in web:
                raise fetch.DuplicateUrlWarning
            web.add_ref(url, e.new_url)
            url = e.new_url
    return url

def process_url(url, rule, queue, web):
    try:
        (fp, filename) = tempfile.mkstemp(prefix=sys.argv[0] + ".")
        url = get_url_w_redirects(fetch.spider, url, filename)
        data = open(filename, 'r').read()

        urls = spider.unbox_it_to_ss(spider.findall(data))
        urls = urlrewrite.rewrite_urls(url, urls)

        for u in urls:
            if u not in web:
                queue.append(u)
                web.add_url(url, [u])

    except fetch.DuplicateUrlWarning:
        pass
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception, e:
        s = traceback.format_exc()
        s += "\nbad url:   |%s|\n" % url
        node = web.get(url)
        for u in node.incoming.keys():
            s += "ref    :   |%s|\n" % u
        s += "\n"
        open("error_log", "a").write(s)
    finally:
        if filename and os.path.exists(filename):
            os.unlink(filename)
        try:
            os.close(fp)
        except:
            pass


#recipe = recipe.load_recipe("rm.py")
recipe = recipe.get_default_recipe()

queue = web.urls()
for rule in recipe:
    depth = rule.get("depth", 1)
    while queue and (depth > 0 or depth < 0):
        if depth > 0: depth -= 1

        working_set = queue
        queue = []
        
        for url in working_set: 
            process_url(url, rule, queue, web)
