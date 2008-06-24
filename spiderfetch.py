#!/usr/bin/env python

import optparse
import os
import pickle
import sys
import tempfile
import traceback

import fetch
import filetype
import io
import recipe
import shcolor
import spider
import urlrewrite
import web


def save_web(wb):
    hostname = urlrewrite.get_hostname(wb.root.url)
    filename = urlrewrite.hostname_to_filename(hostname) + ".web"
    io.write_err("Saving web to %s ..." % shcolor.color(shcolor.YELLOW, filename))
    io.serialize(wb, filename)
    io.write_err(shcolor.color(shcolor.GREEN, "done\n"))

def get_url(getter, url, wb, filename, host_filter=False):
    """http 30x redirects produce a recursion with new urls that may or may not
    have been seen before"""
    while True:
        try:
            getter(url, filename)
            break
        except fetch.ChangedUrlWarning, e:
            if e.new_url in wb:
                raise fetch.DuplicateUrlWarning
            if not recipe.apply_hostfilter(host_filter, e.new_url):
                raise fetch.UrlRedirectsOffHost
            wb.add_ref(url, e.new_url)
            url = e.new_url
    return url

def process_record(record, rule, queue, wb):
    url = record.get("url")
    host_filter = rule.get("host_filter")
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
            url = get_url(getter, url, wb, filename, host_filter=host_filter)

            if record.get("fetch"):
                os.rename(filename, urlrewrite.url_to_filename(url))

            if record.get("spider") and os.path.exists(filename):
                data = open(filename, 'r').read()
                urls = spider.unbox_it_to_ss(spider.findall(data))
                urls = urlrewrite.rewrite_urls(url, urls)

                for u in urls:
                    dum, fet, spi = False, False, False
                    if recipe.apply_mask(rule.get("dump"), u):
                        dum = True
                    if recipe.apply_mask(rule.get("fetch"), u):
                        fet = True
                    if (recipe.apply_mask(rule.get("spider"), u) and
                        recipe.apply_hostfilter(host_filter, u)):
                        spi = True

                    r = {"url" : u, "fetch": False, "spider": False}

                    if u not in wb:
                        if dum:
                            io.write_out("%s\n" % u)
                        if fet:
                            r["fetch"] = True
                        if spi:
                            r["spider"] = True

                        if fet or spi:
                            queue.append(r)

                    if dum or fet or spi:
                        wb.add_url(url, [u])

    except fetch.DuplicateUrlWarning:
        pass
    except fetch.UrlRedirectsOffHost:
        pass
    except KeyboardInterrupt:
        save_web(wb)
        sys.exit(1)
    except Exception, e:
        s = traceback.format_exc()
        s += "\nbad url:   |%s|\n" % url
        node = wb.get(url)
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


def main(url):
    wb = web.Web()
    wb.add_url(url, [])

    #rules = recipe.load_recipe("jpg.py")
    rules = recipe.get_default_recipe(url)

    queue = [{"spider": True, "url": wb.root.url}]
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
                process_record(record, rule, queue, wb)

    save_web(wb)


if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    a("--host", action="store_true", help="Don't spider outside the root host")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    parser.usage = "%prog <url> [options]"
    (opts, args) = parser.parse_args()
    try:
        if opts.host:
            os.environ["HOST_FILTER"] = str(True)
        main(sys.argv[1])
    except IndexError:
        parser.print_help()
