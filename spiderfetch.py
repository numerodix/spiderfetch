#!/usr/bin/env python

import optparse
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
import urlrewrite
import web


def save_session(wb, queue=None):
    hostname = urlrewrite.get_hostname(wb.root.url)
    filename = urlrewrite.hostname_to_filename(hostname)
    io.write_err("Saving session to %s ..." %
         shcolor.color(shcolor.YELLOW, filename+".{web,session}"))
    io.serialize(wb, filename + ".web")
    if queue: 
        io.serialize(queue, filename + ".session")
    # only web being saved, ie. spidering complete, remove old session
    elif os.path.exists(io.logdir(filename + ".session")):
        os.unlink(io.logdir(filename + ".session"))
    io.write_err(shcolor.color(shcolor.GREEN, "done\n"))

def restore_session(url):
    hostname = urlrewrite.get_hostname(url)
    filename = urlrewrite.hostname_to_filename(hostname)
    if (os.path.exists(io.logdir(filename+".session")) and
       os.path.exists(io.logdir(filename+".web"))):
        io.write_err("Restoring session from %s ..." %
             shcolor.color(shcolor.YELLOW, filename+".{web,session}"))
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
            u = urlrewrite.rewrite_urls(url, [e.new_url]).next()
            if u in wb:
                raise fetch.DuplicateUrlWarning
            if not recipe.apply_hostfilter(host_filter, u):
                raise fetch.UrlRedirectsOffHost
            wb.add_ref(url, u)
            url = u
    return url

def process_records(queue, rule, wb):
    newqueue = []
    for record in queue: 
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
                    os.rename(filename,
                      io.safe_filename(urlrewrite.url_to_filename(url)))

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
                                newqueue.append(r)

                        if dum or fet or spi:
                            wb.add_url(url, [u])

        except fetch.DuplicateUrlWarning:
            pass
        except fetch.UrlRedirectsOffHost:
            pass
        except KeyboardInterrupt:
            q = queue[queue.index(record):]
            q.extend(newqueue)
            save_session(wb, queue=q)
            sys.exit(1)
        except Exception, e:
            exc_filename = io.safe_filename("exc", dir=io.LOGDIR)
            io.serialize(e, exc_filename)
            s = traceback.format_exc()
            s += "\nBad url:   |%s|\n" % url
            node = wb.get(url)
            for u in node.incoming.keys():
                s += "Ref    :   |%s|\n" % u
            s += "Exception object serialized to file: %s\n" % exc_filename
            s += "\n"
            io.savelog(s, "error_log", "a")
        finally:
            try:
                if filename and os.path.exists(filename):
                    os.unlink(filename)
                if fp: os.close(fp)
            except (NameError, OSError):
                pass

    return newqueue

def main(queue, rules, wb):
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
            # no more spidering is allowed, so we remove the tags
                for record in queue:
                    if record.get("spider"):
                        # if this isn't the last rule, defer spidering to
                        # outer_queue
                        if rules.index(rule) < len(rules)-1:
                            r = record.copy()
                            r.pop("fetch")
                            outer_queue.append(r)
                        record.pop("spider")

            queue = process_records(queue, rule, wb)

    save_session(wb)


if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "<url> [<pattern>] [options]"
    a("--recipe", metavar="<recipe>", dest="recipe", help="Use a spidering recipe")
    a("--fetch", action="store_true", help="Fetch urls, don't dump")
    a("--dump", action="store_true", help="Dump urls, don't fetch")
    a("--host", action="store_true", help="Only spider this host")
    a("--depth", type="int", metavar="<depth>", dest="depth", help="Spider to this depth")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    (opts, args) = parser.parse_args()
    try:
        if opts.fetch:
            os.environ["FETCH_ALL"] = str(True)
        elif opts.dump:
            os.environ["DUMP_ALL"] = str(True)
        if opts.host:
            os.environ["HOST_FILTER"] = str(True)
        if opts.depth:
            os.environ["DEPTH"] = str(opts.depth)

        url = args[0]
        (q, w) = restore_session(url)
        if opts.recipe:
            rules = recipe.load_recipe(opts.recipe, url)
        else:
            pattern = args[1]
            rules = recipe.get_recipe(pattern, url)
        queue = q or recipe.get_queue(url)
        wb = w or web.Web(url)
    except recipe.PatternError, e:
        io.write_err(shcolor.color(shcolor.RED, "%s\n" % e))
        sys.exit(1)
    except IndexError:
        io.opts_help(None, None, None, parser)
    main(queue, rules, wb)
