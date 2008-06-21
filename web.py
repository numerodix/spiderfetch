#!/usr/bin/env python

import pickle


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



if __name__ == "__main__":
    g = Web()
    g.add_url("no", ["ntnu", "aftenposten"])
    g.add_url("ntnu", ["itea", "ark"])
    print "root:  %s" % g.root.url
    print "no's outgoing:  %s" % [s for s in g.root.outgoing.keys()]
    print "ntnu's incoming:  %s" % [s for s in g.index["ntnu"].incoming.keys()]
    print "ntnu's outgoing:  %s" % [s for s in g.index["ntnu"].outgoing.keys()]
    print "itea's incoming:  %s" % [s for s in g.index["itea"].incoming.keys()]
    print "all nodes:  %s" % [s for s in g.index.keys()]
    print "no" in g
    print "no2" in g
