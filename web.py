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

    ### Introspective

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
        seen = {}
        paths = [[url]]
        seen[url] = True
        while paths:
            paths_next = []
            for path in paths:
                if self.index[path[0]] == self.root:
                    return path
                for url in self.index.get(path[-1]).incoming:
                    if url not in seen:     # loop detected, drop this path
                        seen[url] = True
                        newpath = path[:]   # careful, this is a copy, not ref!
                        newpath.append(url)
                        if self.index[url] == self.root:
                            newpath.reverse()
                            return newpath
                        paths_next.append(newpath)
            paths = paths_next

    # is this supposed to be longest (in graph) or deepest (from root)?
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

    def print_popular(self):
        tuples = [(len(n.incoming), n) for n in self.index.values()]
        tuples.sort(reverse=True)
        for (i, node) in tuples[:10]:
            io.write_err(" %s  %s\n" % (str(i).rjust(2), node.url))

    def print_stats(self):
        s  = "Root url : %s\n" % self.root.url
        s += "Web size : %s urls\n" % len(self.index)
        io.write_err(s)

    ### Pickling

    def _to_pickle(self):
        for node in self.index.values():
            for n in node.incoming:
                node.incoming[n] = None
            for n in node.outgoing:
                node.outgoing[n] = None
        #for node in self.index.values():
        #    print node.incoming
        #    print node.outgoing

    def _from_pickle(self):
        for node in self.index.values():
            for n in node.incoming:
                node.incoming[n] = self.index[n]
            for n in node.outgoing:
                node.outgoing[n] = self.index[n]



if __name__ == "__main__":
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "Usage:  %s <web> [options]\n" % sys.argv[0]
    a("--dump", action="store_true", help="Dump all urls in web")
    a("--in", metavar="<url>", dest="into", help="Find incoming urls to <url>")
    a("--out", metavar="<url>", help="Find outgoing urls from <url>")
    a("--trace", metavar="<url>", help="Trace path from root to <url>")
    a("--longest", action="store_true", help="Show trace of longest path")
    a("--popular", action="store_true", help="Find the most referenced url")
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    a("--test", action="store_true", help="Run trace loop test")
    (opts, args) = parser.parse_args()
    try:
        if opts.test:
            wb = Web()
            wb.root = Node("a")
            wb.index["a"] = wb.root
            wb.index["b"] = Node("b")
            wb.index["c"] = Node("c")
            #wb.index["b"].incoming["a"] = wb.root      # cut link from a to b
            wb.index["b"].incoming["c"] = wb.index["c"] # create loop b <-> c
            wb.index["c"].incoming["b"] = wb.index["b"]
            io.serialize(wb, "web")
            wb = io.deserialize("web")
            print "Root :", wb.root.url
            print "Index:", wb.index
            print "b.in :", wb.index['b'].incoming
            print "c.in :", wb.index['c'].incoming
            wb.print_trace(wb.get_trace("c"))   # inf loop if loop not detected
            sys.exit()

        wb = io.deserialize(args[0])
        if opts.dump:
            wb.dump()
        elif opts.into or opts.out:
            wb.find_refs((opts.into or opts.out), opts.out)
        elif opts.trace:
            wb.print_trace(wb.get_trace(opts.trace))
        elif opts.longest:
            wb.print_trace(wb.longest_path())
        elif opts.popular:
            wb.print_popular()
        else:
            wb.print_stats()
    except IndexError:
        io.opts_help(None, None, None, parser)
