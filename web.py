#!/usr/bin/env python

import optparse
import pickle
import sys

import io


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
        
    def find_refs(self, url, out=True):
        node = self.index.get(url)
        l = node.outgoing
        if not out: l = node.incoming
        for u in l:
            io.write_err("%s\n" % u)

    def trace(self, url):
        node = self.index.get(url)
        if node:
            queue = node.incoming.keys()


    def print_stats(self):
        s  = "Root url : %s\n" % self.root.url
        s += "Web size : %s urls\n" % len(self.index)
        io.write_err(s)


if __name__ == "__main__":
    parser = optparse.OptionParser() ; a = parser.add_option
    a("--all", action="store_true", help="List all urls in web")
    a("--in", dest="into", help="Find incoming urls to $url")
    a("--out", help="Find outgoing urls from $url")
    a("--trace", help="Trace path from root to $url")
    (opts, args) = parser.parse_args()
    try:
        web = io.deserialize(args[0])
        if opts.all:
            web.dump()
        elif opts.into or opts.out:
            web.find_refs((opts.into or opts.out), opts.out)
        elif opts.trace:
            web.trace(opts.trace)
        else:
            web.print_stats()
    except IndexError:
        parser.print_help()
