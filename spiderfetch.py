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


def save_session(wb, queue=None):
    hostname = urlrewrite.get_hostname(wb.root.url)
    filename = urlrewrite.hostname_to_filename(hostname)
    io.write_err("Saving session to %s ..." % shcolor.color(shcolor.YELLOW, filename))
    io.serialize(wb, filename + ".web")
    if queue: 
        io.serialize(queue, filename + ".session")
    io.write_err(shcolor.color(shcolor.GREEN, "done\n"))

def restore_session(url):
    hostname = urlrewrite.get_hostname(url)
    filename = urlrewrite.hostname_to_filename(hostname)
    if os.path.exists(filename+".session") and os.path.exists(filename+".web"):
        io.write_err("Restoring session from %s ..." %\
                     shcolor.color(shcolor.YELLOW, filename))
        q = io.deserialize(filename + ".session")
        q = recipe.overrule_records(q)
        wb = io.deserialize(filename + ".web")
        io.write_err(shcolor.color(shcolor.GREEN, "done\n"))
        return q, wb
    return None, None


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

def process_records(working_set, queue, rule, wb):
    for record in working_set: 
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
            q = working_set[working_set.index(record):]
            q.extend(queue)
            save_session(wb, queue=q)
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


def main(url, queue=None, wb=None):
    if not wb:
        wb = web.Web()
        wb.add_url(url, [])

    #rules = recipe.load_recipe("jpg.py")
    rules = recipe.get_default_recipe(url)

    queue = queue or [{"spider": True, "url": wb.root.url}]
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

            process_records(working_set, queue, rule, wb)

    save_session(wb)


if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "Usage:  %s <url> [<pattern>] [options]\n" % sys.argv[0]
    a("--fetch", action="store_true", help="Fetch urls, don't dump")
    a("--dump", action="store_true", help="Dump urls, don't fetch")
    a("--host", action="store_true", help="Only spider this host")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    (opts, args) = parser.parse_args()
    try:
        if opts.fetch:
            os.environ["FETCH_ALL"] = str(True)
        elif opts.dump:
            os.environ["DUMP_ALL"] = str(True)
        if opts.host:
            os.environ["HOST_FILTER"] = str(True)
        url = args[0]
        (q, w) = restore_session(url)
        main(url, queue=q, wb=w)
    except IndexError:
        io.opts_help(None, None, None, parser)
