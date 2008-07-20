#!/usr/bin/env python

import pickle
import sys

import io
import shcolor


class Node(object):
    def __init__(self, url):
        self._url = url
        self._incoming = {}
        self._outgoing = {}
        self._aliases = [url]

class Web(object):
    def __init__(self, url_root=None):
        self._root = None
        self._index = {}

        if url_root:
            self.set_root(url_root)


    ## root

    def get_root_node(self):
        return self._root

    def get_root(self):
        return self.get_root_node()._url

    def set_root(self, url):
        self.add_node(url)
        node = self.get_node(url)
        self._root = node

    ## index

    def add_node(self, url):
        if url not in self._index:
            self._index[url] = Node(url)

    def get_node(self, url):
        return self._index[url]

    ## index public

    def get_iterurls(self):
        return self._index.keys()

    def add_url(self, url, children):
        self.add_node(url)
        self.add_incoming(url, children)
        self.add_outgoing(url, children)

    def add_ref(self, url, new_url):
        self._index[new_url] = self._index[url]
        self.add_alias(url, new_url)

    def __contains__(self, url):
        return url in self._index

    def __len__(self):
        return len(self._index)

    def __str__(self):
        return ", ".join(u for u in self.get_iterurls())


    ## incoming

    def add_incoming(self, url, children):
        node = self.get_node(url)
        for c_url in children:
            self.add_node(c_url)
            n = self.get_node(c_url)
            n._incoming[url] = node

    def get_iterincoming(self, url):
        return (u for u in self.get_node(url)._incoming)

    def len_incoming(self, url):
        return len(self.get_node(url)._incoming)

    ## outgoing

    def add_outgoing(self, url, children):
        node = self.get_node(url)
        for c_url in children:
            self.add_node(c_url)
            n = self.get_node(c_url)
            node._outgoing[c_url] = n

    def get_iteroutgoing(self, url):
        return (u for u in self.get_node(url)._outgoing)

    ## aliases

    def add_alias(self, url, url_alias):
        if not url == url_alias:
            self.get_node(url)._aliases.append(url_alias)

    def get_iteraliases(self, url):
        return (a for a in self.get_node(url)._aliases)

    def len_aliases(self, url):
        return len(self.get_node(url)._aliases)


    ### Introspective

    def dump(self):
        for u in self.get_iterurls():
            io.write_out("%s\n" % u)

    def assert_in_web(self, url):
        if url not in self:
            io.write_err("Url %s not in the web\n" %
                         shcolor.color(shcolor.YELLOW, url))
            sys.exit(1)
        
    def print_refs(self, url, out=True):
        self.assert_in_web(url)
        it = self.get_iteroutgoing(url)
        if not out:
            it = self.get_iterincoming(url)
        for u in it:
            io.write_out("%s\n" % u)

    def print_aliases(self, url):
        self.assert_in_web(url)
        for u in self.get_iteraliases(url):
            io.write_out("%s\n" % u)

    def get_trace(self, url):
        self.assert_in_web(url)
        seen = {}
        paths = [[url]]
        seen[url] = True
        while paths:
            paths_next = []
            for path in paths:
                if self.get_node(path[0]) == self.get_root_node():
                    return path
                for url in self.get_iterincoming(path[-1]):
                    if url not in seen:     # loop detected, drop this path
                        seen[url] = True
                        newpath = path[:]   # careful, this is a copy, not ref!
                        newpath.append(url)
                        if self.get_node(url) == self.get_root_node():
                            newpath.reverse()
                            return newpath
                        paths_next.append(newpath)
            paths = paths_next

    # is this supposed to be longest (in graph) or deepest (from root)?
    def deepest_url(self):
        paths = []
        for url in self.get_iterurls():
            tr = self.get_trace(url)
            tr and paths.append(tr)
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
        tuples = [(self.len_incoming(u), u) for u in self.get_iterurls()]
        tuples.sort(reverse=True)
        ln = len(str(tuples[0][0]).rjust(2))
        io.write_err("Showing most referenced urls:\n")
        for (i, u) in tuples[:10]:
            io.write_err(" %s  %s\n" % (str(i).rjust(ln), u))

    def print_multiple(self):
        ss = []
        for u in self.get_iterurls():
            ln = self.len_aliases(u)
            if ln > 1:
                pair = (ln, [a for a in self.get_iteraliases(u)])
                if pair not in ss:
                    ss.append(pair)
        if ss:
            ss.sort(reverse=True)
            ln = len(str(ss[0][0]))  # length of highest count
            io.write_err("Showing documents with multiple urls:\n")
            for pair in ss:
                (count, aliases) = pair
                for url in aliases:
                    prefix = "".rjust(ln)
                    if aliases.index(url) == 0:
                        prefix = str(count).rjust(ln)
                    io.write_err(" %s  %s\n" % (prefix, url))
                if not ss.index(pair) == len(ss)-1:
                    io.write_err("\n")

    def print_stats(self):
        s  = "Root url : %s\n" % self.get_root()
        s += "Web size : %s urls\n" % len(self)
        io.write_err(s)

    ### Pickling

    def _to_pickle(self):
        for node in self._index.itervalues():
            for n in node._incoming:
                node._incoming[n] = None
            for n in node._outgoing:
                node._outgoing[n] = None

    def _from_pickle(self):
        for node in self._index.itervalues():
            for n in node._incoming:
                node._incoming[n] = self._index[n]
            for n in node._outgoing:
                node._outgoing[n] = self._index[n]



if __name__ == "__main__":
    (parser, a) = io.init_opts("<web> [options]")
    a("--dump", action="store_true", help="Dump all urls in web")
    a("--in", metavar="<url>", dest="into", help="Find incoming urls to <url>")
    a("--out", metavar="<url>", help="Find outgoing urls from <url>")
    a("--aliases", metavar="<url>", help="Find other urls for the document at <url>")
    a("--multiple", action="store_true", help="Find documents with multiple urls")
    a("--trace", metavar="<url>", help="Trace path from root to <url>")
    a("--deepest", action="store_true", help="Trace url furthest from root")
    a("--popular", action="store_true", help="Find the most referenced urls")
    a("--test", action="store_true", help="Run trace loop test")
    (opts, args) = io.parse_args(parser)
    try:
        if opts.test:
            wb = Web()

            wb.set_root('a')
            wb.add_ref('a', 'adupe')
            wb.add_url('a', ['b'])
            wb.add_url('b', ['c'])
            wb.add_url('d', ['e'])      # disconnected from root
            wb.add_incoming('d', 'e')
            wb.add_incoming('e', 'd')   # create loop b <-> c

            io.serialize(wb, "web")
            wb = io.deserialize("web")

            io.write_err("Root :  %s\n" % wb.get_root())
            io.write_err("Web  :  %s\n" % wb)
            io.write_err("d.in :  %s\n" % ", ".join(u for u in wb.get_iterincoming('d')))
            io.write_err("e.in :  %s\n" % ", ".join(u for u in wb.get_iterincoming('e')))

            io.write_header('stats()')
            wb.print_stats()
            io.write_header('dump()')
            wb.dump()
            io.write_header('print_refs(e, out=False)')
            wb.print_refs('e', out=False)
            io.write_header('print_aliases(a)')
            wb.print_aliases('a')
            io.write_header('print_multiple()')
            wb.print_multiple()
            io.write_header('print_trace(c)')
            wb.print_trace(wb.get_trace("c"))   # inf loop if loop not detected
            io.write_header('print_trace(e)')
            wb.print_trace(wb.get_trace("e"))   # inf loop if loop not detected
            io.write_header('deepest_url()')
            wb.print_trace(wb.deepest_url())
            io.write_header('print_popular()')
            wb.print_popular()

            sys.exit()

        wb = io.deserialize(args[0])
        if opts.dump:
            wb.dump()
        elif opts.into or opts.out:
            wb.print_refs((opts.into or opts.out), opts.out)
        elif opts.aliases:
            wb.print_aliases(opts.aliases)
        elif opts.multiple:
            wb.print_multiple()
        elif opts.trace:
            wb.print_trace(wb.get_trace(opts.trace))
        elif opts.deepest:
            wb.print_trace(wb.deepest_url())
        elif opts.popular:
            wb.print_popular()
        else:
            wb.print_stats()
    except IndexError:
        io.opts_help(None, None, None, parser)
