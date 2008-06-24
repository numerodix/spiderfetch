#!/usr/bin/env python

import optparse
import pickle
import sys

import io
import shcolor


class Node(object):
    def __init__(self, url):
        self.url = url
        self.incoming = {}
        self.outgoing = {}

class Web(object):
    def __init__(self):
        self.root = None
        self.index = {}

    def __contains__(self, e):
        return e in self.index

    def __str__(self):
        return str(self.index)

    def urls(self):
        return self.index.keys()

    def add_url(self, url, children):
        if url not in self.index:
            self.index[url] = Node(url)
        node = self.index[url]

        if not self.root:
            self.root = node

        for c_url in children:
            if not c_url == url:
                if c_url not in self.index:
                    self.index[c_url] = Node(c_url)
                n = self.index[c_url]
                n.incoming[node.url] = node
                node.outgoing[n.url] = n

    def add_ref(self, url, new_url):
        self.index[new_url] = self.index[url]

    def get(self, url):
        return self.index.get(url)


    def dump(self):
        for u in self.index:
            io.write_err("%s\n" % u)

    def assert_in_web(self, url):
        if url not in self.index:
            io.write_err("Url %s not in the web\n" %
                         shcolor.color(shcolor.YELLOW, url))
            sys.exit(1)
        
    def find_refs(self, url, out=True):
        self.assert_in_web(url)
        node = self.index.get(url)
        l = node.outgoing
        if not out: l = node.incoming
        for u in l:
            io.write_err("%s\n" % u)

    def get_trace(self, url):
        self.assert_in_web(url)
        def find_path_to_root(paths):
            while paths:
                paths_next = []
                for path in paths:
                    if path[0] == self.root.url:
                        return path
                    for url in self.index.get(path[-1]).incoming:
                        newpath = path[:]   # careful, this is a copy, not ref!
                        newpath.append(url)
                        if url == self.root.url:
                            return newpath
                        paths_next.append(newpath)
                paths = paths_next
        hops = find_path_to_root([[url]])
        hops.reverse()
        return hops

    def longest_path(self):
        paths = []
        for url in self.index:
            paths.append(self.get_trace(url))
        longest = paths[0]
        for path in paths:
            if len(path) > len(longest):
                longest = path
        return longest

    def print_trace(self, path):
        if path:
            io.write_err("Showing trace from root:\n")
            for (i, hop) in enumerate(path):
                io.write_err(" %s  %s\n" % (str(i).rjust(1+(len(path)/10)), hop))

    def print_stats(self):
        s  = "Root url : %s\n" % self.root.url
        s += "Web size : %s urls\n" % len(self.index)
        io.write_err(s)



if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "%prog <web> [options]"
    a("--dump", action="store_true", help="Dump all urls in web")
    a("--in", metavar="<url>", dest="into", help="Find incoming urls to <url>")
    a("--out", metavar="<url>", help="Find outgoing urls from <url>")
    a("--trace", metavar="<url>", help="Trace path from root to <url>")
    a("--longest", action="store_true", help="Show trace of longest path")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    (opts, args) = parser.parse_args()
    try:
        web = io.deserialize(args[0])
        if opts.dump:
            web.dump()
        elif opts.into or opts.out:
            web.find_refs((opts.into or opts.out), opts.out)
        elif opts.trace:
            web.print_trace(web.get_trace(opts.trace))
        elif opts.longest:
            web.print_trace(web.longest_path())
        else:
            web.print_stats()
    except IndexError:
        parser.print_help()
