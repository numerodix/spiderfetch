#!/usr/bin/env python

import pickle


class Node(object):
    def __init__(self, url):
        self.url = url
        self.incoming = {}
        self.outgoing = {}

class UrlGraph(object):
    def __init__(self):
        self.root = None
        self.index = {}

    def add_url(self, url, children):
        if url not in self.index:
            self.index[url] = Node(url)
        node = self.index[url]

        if not self.root:
            self.root = node

        for c_url in children:
            if c_url not in self.index:
                self.index[c_url] = Node(c_url)
            n = self.index[c_url]
            n.incoming[node.url] = node
            node.outgoing[n.url] = n



if __name__ == "__main__":
    g = UrlGraph()
    g.add_url("no", ["ntnu", "aftenposten"])
    g.add_url("ntnu", ["itea", "ark"])
    print "root:  %s" % g.root.url
    print "no's outgoing:  %s" % [s for s in g.root.outgoing.keys()]
    print "ntnu's incoming:  %s" % [s for s in g.index["ntnu"].incoming.keys()]
    print "ntnu's outgoing:  %s" % [s for s in g.index["ntnu"].outgoing.keys()]
    print "itea's incoming:  %s" % [s for s in g.index["itea"].incoming.keys()]
    print "all nodes:  %s" % [s for s in g.index.keys()]
