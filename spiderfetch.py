#!/usr/bin/env python

import os
import pickle
import sys
import tempfile
import traceback

import fetch
import filetype
import io
import recipe
import spider
import urlrewrite
import web


url = sys.argv[1]
web = web.Web()
web.add_url(url, [])

def write_out(s):
    sys.stdout.write(s)

def save_web(web):
    hostname = urlrewrite.get_hostname(web.root.url)
    filename = urlrewrite.hostname_to_filename(hostname) + ".web"
    io.serialize(web, filename)

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

def process_record(record, rule, queue, web):
    url = record.get("url")
    try:
        getter = None
        if record.get("fetch") and record.get("spider"):
            getter = fetch.spider_fetch
        elif record.get("fetch"):
            getter = fetch.fetch
        elif record.get("spider"):
            getter = fetch.spider

        if getter:
            (fp, filename) = io.get_tempfile()
            url = get_url_w_redirects(getter, url, filename)

            if record.get("fetch"):
                os.rename(filename, urlrewrite.url_to_filename(url))

            if record.get("spider") and os.path.exists(filename):
                data = open(filename, 'r').read()
                urls = spider.unbox_it_to_ss(spider.findall(data))
                urls = urlrewrite.rewrite_urls(url, urls)

                for u in urls:
                    if u not in web:
                        r = {"url" : u, "spider": False, "fetch": False}

                        if recipe.apply_mask(rule.get("dump"), u):
                            write_out("%s\n" % u)
                            web.add_url(url, [u])
                        if recipe.apply_mask(rule.get("fetch"), u):
                            r["fetch"] = True
                            web.add_url(url, [u])
                        if (recipe.apply_mask(rule.get("spider"), u) and
                            recipe.apply_mask(rule.get("host_filter"), u)):
                            r["spider"] = True
                            web.add_url(url, [u])

                        if r["spider"] or r["fetch"]:
                            queue.append(r)

    except fetch.DuplicateUrlWarning:
        pass
    except KeyboardInterrupt:
        save_web(web)
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
        try:
            if filename and os.path.exists(filename):
                os.unlink(filename)
            if fp: os.close(fp)
        except (NameError, OSError):
            pass


#rules = recipe.load_recipe("jpg.py")
rules = recipe.get_default_recipe(url)

queue = [{"spider": True, "url": web.root.url}]
for rule in rules:
    depth = rule.get("depth", 1)
    while queue:
        if depth > 0: 
            depth -= 1
        elif depth == 0:
        # There may still be records in the queue, but since depth is reached
        # no more spidering is allowed, so we remove the tags
            map(lambda r: r.pop("spider"), queue)
        
        working_set = queue
        queue = []
        
        for record in working_set: 
            process_record(record, rule, queue, web)

save_web(web)
