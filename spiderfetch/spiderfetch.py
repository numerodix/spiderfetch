#!/usr/bin/env python
#
# <desc> Web spider and fetcher </desc>

from __future__ import absolute_import

import os
import shutil
import sys
import traceback
import time

import ansicolor

from spiderfetch import fetch
from spiderfetch import ioutils
from spiderfetch import recipe
from spiderfetch import spider
from spiderfetch import urlrewrite
from spiderfetch import web


class Session(object):
    def __init__(self, wb=None, queue=None, rules=None):
        self.wb = wb
        self.queue = queue
        self.rules = rules

        # well, not really, it may not have been saved yet
        self.last_save = time.time()

        self.save_interval = 60 * 30  # 30min

    def save(self):
        hostname = urlrewrite.get_hostname(self.wb.root.url)
        filename = urlrewrite.hostname_to_filename(hostname)
        ioutils.write_err("Saving session to %s ..." %
                        ansicolor.yellow(filename + ".{web,session}"))
        ioutils.serialize(self.wb, filename + ".web", dir=ioutils.LOGDIR)
        if self.queue:
            ioutils.serialize(self.queue, filename + ".session", dir=ioutils.LOGDIR)
        # only web being saved, ie. spidering complete, remove old session
        elif ioutils.file_exists(filename + ".session", dir=ioutils.LOGDIR):
            ioutils.delete(filename + ".session", dir=ioutils.LOGDIR)
        ioutils.write_err(ansicolor.green("done\n"))

    def maybe_save(self):
        t = time.time()
        if self.last_save + self.save_interval < t:
            self.save()
            self.last_save = t

    @classmethod
    def restore(cls, url):
        hostname = urlrewrite.get_hostname(url)
        filename = urlrewrite.hostname_to_filename(hostname)
        q, wb = None, None
        if (ioutils.file_exists(filename + ".web", dir=ioutils.LOGDIR)):
            ioutils.write_err("Restoring web from %s ..." %
                            ansicolor.yellow(filename + ".web"))
            wb = ioutils.deserialize(filename + ".web", dir=ioutils.LOGDIR)
            ioutils.write_err(ansicolor.green("done\n"))
        if (ioutils.file_exists(filename + ".session", dir=ioutils.LOGDIR)):
            ioutils.write_err("Restoring session from %s ..." %
                            ansicolor.yellow(filename + ".session"))
            q = ioutils.deserialize(filename + ".session", dir=ioutils.LOGDIR)
            q = recipe.overrule_records(q)
            ioutils.write_err(ansicolor.green("done\n"))
        return cls(wb=wb, queue=q)


class SpiderFetcher(object):
    def __init__(self, session):
        self.session = session

    def log_exc(self, exc, url):
        exc_filename = ioutils.safe_filename("exc", dir=ioutils.LOGDIR)
        ioutils.serialize(exc, exc_filename, dir=ioutils.LOGDIR)
        s = traceback.format_exc()
        s += "\nBad url:   |%s|\n" % url
        node = self.session.wb.get(url)
        for u in node.incoming.keys():
            s += "Ref    :   |%s|\n" % u
        s += "Exception object serialized to file: %s\n\n" % exc_filename
        ioutils.savelog(s, "error_log", "a")

    def get_url(self, fetcher, host_filter=False):
        """http 30x redirects produce a recursion with new urls that may or may not
        have been seen before"""
        while True:
            try:
                fetcher.launch_w_tries()
                break
            except fetch.ChangedUrlWarning as e:
                url = urlrewrite.rewrite_urls(fetcher.url, [e.new_url]).next()
                if url in self.session.wb:
                    raise fetch.DuplicateUrlWarning
                if not recipe.apply_hostfilter(host_filter, url):
                    raise fetch.UrlRedirectsOffHost
                self.session.wb.add_ref(fetcher.url, url)
                fetcher.url = url
        return fetcher.url

    def qualify_urls(self, ref_url, urls, rule, newqueue):
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
            record = {"url": url}
            if url not in self.session.wb:
                if _dump:
                    ioutils.write_out("%s\n" % url)
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
                self.session.wb.add_url(ref_url, [url])

        return newqueue

    def process_records(self, rule):
        newqueue = []
        for record in self.session.queue:
            self.session.maybe_save()

            url = record.get("url")
            try:
                (fp, filename) = ioutils.get_tempfile()
                f = fetch.Fetcher(mode=record.get("mode"), url=url, filename=filename)
                url = self.get_url(f, host_filter=rule.get("host_filter"))
                filename = f.filename

                # consider retrying the fetch if it failed
                if f.error and fetch.err.is_temporal(f.error):
                    if not record.get("retry"):
                        record["retry"] = True
                        self.session.queue.append(record)

                if record.get("mode") == fetch.Fetcher.SPIDER:
                    data = open(filename, 'r').read()
                    urls = spider.unbox_it_to_ss(spider.findall(data, url))
                    urls = urlrewrite.rewrite_urls(url, urls)

                    newqueue = self.qualify_urls(url, urls, rule, newqueue)

                if record.get("mode") == fetch.Fetcher.FETCH:
                    shutil.move(filename,
                                ioutils.safe_filename(urlrewrite.url_to_filename(url)))

            except (fetch.DuplicateUrlWarning, fetch.UrlRedirectsOffHost):
                pass
            except KeyboardInterrupt:
                q = self.session.queue[self.session.queue.index(record):]
                q.extend(newqueue)
                self.session.queue = q
                self.session.save()
                sys.exit(1)
            except Exception as exc:
                self.log_exc(exc, url)
            finally:
                try:
                    if filename and os.path.exists(filename):
                        os.unlink(filename)
                    if fp:
                        os.close(fp)
                except (NameError, OSError):
                    pass

            pause = os.environ.get('PAUSE')
            if pause:
                time.sleep(int(pause))

        return newqueue

    def split_queue(self, lastrule=False):
        fetch_queue, spider_queue = [], []
        for record in self.session.queue:
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

    def main(self):
        outer_queue = self.session.queue
        for rule in self.session.rules:
            depth = rule.get("depth", 1)

            # queue will be exhausted in inner loop, but once depth is reached
            # the contents to spider will fall through to outer_queue
            outer_queue, self.session.queue = [], outer_queue

            while self.session.queue:
                if depth > 0:
                    depth -= 1

                # There may still be records in the queue, but since depth is reached
                # no more spidering is allowed, so we allow one more iteration, but
                # only for fetching
                elif depth == 0:
                    self.session.queue, outer_queue = self.split_queue(
                        self.session.rules.index(rule) == len(self.session.rules) - 1)

                self.session.queue = self.process_records(rule)

        self.session.save()


def run_script():
    (parser, a) = ioutils.init_opts("<url> ['<pattern>'] [options]")
    a("--recipe", metavar="<recipe>", dest="recipe", help="Use a spidering recipe")
    a("--fetch", action="store_true", help="Fetch urls, don't dump")
    a("--dump", action="store_true", help="Dump urls, don't fetch")
    a("--host", action="store_true", help="Only spider this host")
    a("--pause", type="int", metavar="<pause>", dest="pause", help="Pause for x seconds between requests")
    a("--depth", type="int", metavar="<depth>", dest="depth", help="Spider to this depth")
    (opts, args) = ioutils.parse_args(parser)
    try:
        if opts.fetch:
            os.environ["FETCH_ALL"] = "1"
        elif opts.dump:
            os.environ["DUMP_ALL"] = "1"
        if opts.host:
            os.environ["HOST_FILTER"] = "1"
        if opts.pause:
            os.environ["PAUSE"] = str(opts.pause)
        if opts.depth:
            os.environ["DEPTH"] = str(opts.depth)

        url = args[0]
        if opts.recipe:
            rules = recipe.load_recipe(opts.recipe, url)
        else:
            pattern = args[1]
            rules = recipe.get_recipe(pattern, url)

        session = Session.restore(url)
        session.rules = rules

        if session.queue is None:
            session.queue = recipe.get_queue(url, mode=fetch.Fetcher.SPIDER)
        if session.wb is None:
            session.wb = web.Web(url)

    except recipe.PatternError as e:
        ioutils.write_err(ansicolor.red("%s\n" % e))
        sys.exit(1)
    except IndexError:
        ioutils.opts_help(None, None, None, parser)

    spiderfetcher = SpiderFetcher(session)
    spiderfetcher.main()


if __name__ == "__main__":
    run_script()
