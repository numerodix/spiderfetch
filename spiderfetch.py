#!/usr/bin/env python

import os
import re
import sys
import tempfile
import traceback

import fetch
import filetype
import io
import recipe
import shcolor
import spider
import time
import urlrewrite
import web


class SpiderFetch(object):
    def __init__(self):
        self.save_interval = 60*30
        self.last_save = time.time()

    def save_session(self, wb, queue=None):
        hostname = urlrewrite.get_hostname(wb.root.url)
        filename = urlrewrite.hostname_to_filename(hostname)
        io.write_err("Saving session to %s ..." %
             shcolor.color(shcolor.YELLOW, filename+".{web,session}"))
        io.serialize(wb, filename + ".web", dir=io.LOGDIR)
        if queue:
            io.serialize(queue, filename + ".session", dir=io.LOGDIR)
        # only web being saved, ie. spidering complete, remove old session
        elif io.file_exists(filename + ".session", dir=io.LOGDIR):
            io.delete(filename + ".session", dir=io.LOGDIR)
        io.write_err(shcolor.color(shcolor.GREEN, "done\n"))

    def maybesave(self, wb, queue):
        t = time.time()
        if self.last_save + self.save_interval < t:
            self.save_session(wb, queue=queue)
            self.last_save = t

    def restore_session(self, url):
        hostname = urlrewrite.get_hostname(url)
        filename = urlrewrite.hostname_to_filename(hostname)
        if (io.file_exists(filename + ".session", dir=io.LOGDIR) and
            io.file_exists(filename + ".web", dir=io.LOGDIR)):
            io.write_err("Restoring session from %s ..." %
                 shcolor.color(shcolor.YELLOW, filename+".{web,session}"))
            q = io.deserialize(filename + ".session", dir=io.LOGDIR)
            q = recipe.overrule_records(q)
            wb = io.deserialize(filename + ".web", dir=io.LOGDIR)
            io.write_err(shcolor.color(shcolor.GREEN, "done\n"))
            return q, wb
        return None, None

    def log_exc(self, exc, url, wb):
        exc_filename = io.safe_filename("exc", dir=io.LOGDIR)
        io.serialize(exc, exc_filename, dir=io.LOGDIR)
        s = traceback.format_exc()
        s += "\nBad url:   |%s|\n" % url
        node = wb.get(url)
        for u in node.incoming.keys():
            s += "Ref    :   |%s|\n" % u
        s += "Exception object serialized to file: %s\n\n" % exc_filename
        io.savelog(s, "error_log", "a")

    def get_url(self, fetcher, wb, host_filter=False):
        """http 30x redirects produce a recursion with new urls that may or may not
        have been seen before"""
        while True:
            try:
                fetcher.launch()
                break
            except fetch.ChangedUrlWarning, e:
                url = urlrewrite.rewrite_urls(fetcher.url, [e.new_url]).next()
                if url in wb:
                    raise fetch.DuplicateUrlWarning
                if not recipe.apply_hostfilter(host_filter, url):
                    raise fetch.UrlRedirectsOffHost
                wb.add_ref(fetcher.url, url)
                fetcher.url = url
        return fetcher.url

    def qualify_urls(self, ref_url, urls, rule, newqueue, wb):
        for url in urls:
            _dump, _fetch, _spider = False, False, False

            # apply patterns to determine how to qualify url
            if recipe.apply_mask(rule.get("dump"), url):
                _dump = True
            if recipe.apply_mask(rule.get("fetch"), url):
                _fetch = True
            if (recipe.apply_mask(rule.get("spider"), url) and
                recipe.apply_hostfilter(rule.get("host_filter"), url)):
                _spider = True

            # build a record based on qualification
            record = {"url" : url}
            if url not in wb:
                if _dump:
                    io.write_out("%s\n" % url)
                if _fetch and _spider:
                    record["mode"] = fetch.Fetcher.SPIDER_FETCH
                elif _fetch:
                    record["mode"] = fetch.Fetcher.FETCH
                elif _spider:
                    record["mode"] = fetch.Fetcher.SPIDER

                if _fetch or _spider:
                    newqueue.append(record)

            # add url to web if it was matched by anything
            if _dump or _fetch or _spider:
                wb.add_url(ref_url, [url])

        return newqueue, wb

    def process_records(self, queue, rule, wb):
        newqueue = []
        for record in queue:
            self.maybesave(wb, queue)

            url = record.get("url")
            try:
                (fp, filename) = io.get_tempfile()
                f = fetch.Fetcher(mode=record.get("mode"), url=url, filename=filename)
                url = self.get_url(f, wb, host_filter=rule.get("host_filter"))
                filename = f.filename

                # consider retrying the fetch if it failed
                if f.error and fetch.err.is_temporal(f.error):
                    if not record.get("retry"):
                        record["retry"] = True
                        queue.append(record)

                if record.get("mode") == fetch.Fetcher.SPIDER:
                    data = open(filename, 'r').read()
                    urls = spider.unbox_it_to_ss(spider.findall(data, url))
                    urls = urlrewrite.rewrite_urls(url, urls)

                    (newqueue, wb) = self.qualify_urls(url, urls, rule, newqueue, wb)

                if record.get("mode") == fetch.Fetcher.FETCH:
                    os.rename(filename,
                      io.safe_filename(urlrewrite.url_to_filename(url)))

            except (fetch.DuplicateUrlWarning, fetch.UrlRedirectsOffHost):
                pass
            except KeyboardInterrupt:
                q = queue[queue.index(record):]
                q.extend(newqueue)
                self.save_session(wb, queue=q)
                sys.exit(1)
            except Exception, exc:
                self.log_exc(exc, url, wb)
            finally:
                try:
                    if filename and os.path.exists(filename):
                        os.unlink(filename)
                    if fp: os.close(fp)
                except (NameError, OSError):
                    pass

        return newqueue

    def split_queue(self, queue, lastrule=False):
        fetch_queue, spider_queue = [], []
        for record in queue:
            mode = record.get("mode")
            if mode == fetch.Fetcher.FETCH or mode == fetch.Fetcher.SPIDER_FETCH:
                r = record.copy()
                r["mode"] = fetch.Fetcher.FETCH
                fetch_queue.append(r)
            # if this isn't the last rule, defer remaining spidering to the
            # next rule
            if not lastrule:
                if mode == fetch.Fetcher.SPIDER or mode == fetch.Fetcher.SPIDER_FETCH:
                    r = record.copy()
                    r["mode"] = fetch.Fetcher.SPIDER
                    spider_queue.append(r)
        return fetch_queue, spider_queue

    def run(self, queue, rules, wb):
        outer_queue = queue
        for rule in rules:
            depth = rule.get("depth", 1)

            # queue will be exhausted in inner loop, but once depth is reached
            # the contents to spider will fall through to outer_queue
            outer_queue, queue = [], outer_queue

            while queue:
                if depth > 0:
                    depth -= 1
                elif depth == 0:
                # There may still be records in the queue, but since depth is reached
                # no more spidering is allowed, so we allow one more iteration, but
                # only for fetching
                    queue, outer_queue = self.split_queue(queue, 
                                          rules.index(rule) == len(rules)-1)

                queue = self.process_records(queue, rule, wb)

        self.save_session(wb)


if __name__ == "__main__":
    (parser, a) = io.init_opts("<url> ['<pattern>'] [options]")
    a("--recipe", metavar="<recipe>", dest="recipe", help="Use a spidering recipe")
    a("--fetch", action="store_true", help="Fetch urls, don't dump")
    a("--dump", action="store_true", help="Dump urls, don't fetch")
    a("--host", action="store_true", help="Only spider this host")
    a("--depth", type="int", metavar="<depth>", dest="depth", help="Spider to this depth")
    (opts, args) = io.parse_args(parser)
    try:
        if opts.fetch:
            os.environ["FETCH_ALL"] = "1"
        elif opts.dump:
            os.environ["DUMP_ALL"] = "1"
        if opts.host:
            os.environ["HOST_FILTER"] = "1"
        if opts.depth:
            os.environ["DEPTH"] = str(opts.depth)

        sp = SpiderFetch()
        url = args[0]
        (q, w) = sp.restore_session(url)
        if opts.recipe:
            rules = recipe.load_recipe(opts.recipe, url)
        else:
            pattern = args[1]
            rules = recipe.get_recipe(pattern, url)
        queue = q or recipe.get_queue(url, mode=fetch.Fetcher.SPIDER)
        wb = w or web.Web(url)
    except recipe.PatternError, e:
        io.write_err(shcolor.color(shcolor.RED, "%s\n" % e))
        sys.exit(1)
    except IndexError:
        io.opts_help(None, None, None, parser)
    sp.run(queue, rules, wb)
