#!/usr/bin/env python

import pickle
import os
import sqlite3
import sys

import io
import shcolor


EXT_MEM = '.web'
EXT_SQL = '.websq'

class Node(object):
    def __init__(self, url, id=None):
        self.url = url
        self.incoming = {}
        self.outgoing = {}
        self.aliases = [url]
        if id:
            self.id = id
        else:
            self.id = hash(self)

    def __cmp__(self, another):
        return cmp(self.id, another.id)

class Web(object):
    def __init__(self, url_root=None):
        self.root = None
        self.index = {}

        if url_root:
            self.set_root(url_root)

    ### Pickling

    def _to_pickle(self):
        for node in self.index.itervalues():
            for n in node.incoming:
                node.incoming[n] = None
            for n in node.outgoing:
                node.outgoing[n] = None

    def _from_pickle(self):
        for node in self.index.itervalues():
            for n in node.incoming:
                node.incoming[n] = self.index[n]
            for n in node.outgoing:
                node.outgoing[n] = self.index[n]

    ## root

    def get_root_node(self):
        return self.root

    def get_root(self):
        return self.get_root_node().url

    def set_root(self, url):
        self.add_node(url)
        node = self.get_node(url)
        self.root = node

    ## index

    def add_node(self, url):
        if url not in self.index:
            self.index[url] = Node(url)

    def get_node(self, url):
        return self.index[url]

    ## index public

    def get_iterurls(self):
        return self.index.keys()

    def add_url(self, url, children):
        self.add_node(url)
        self.add_incoming(url, children)
        self.add_outgoing(url, children)

    def __contains__(self, url):
        return url in self.index

    def __len__(self):
        return len(self.index)

    def __str__(self):
        return ", ".join(u for u in self.get_iterurls())

    ## incoming

    def add_incoming(self, url, children):
        node = self.get_node(url)
        for c_url in children:
            self.add_node(c_url)
            n = self.get_node(c_url)
            n.incoming[url] = node

    def get_iterincoming(self, url):
        return (u for u in self.get_node(url).incoming)

    def len_incoming(self, url):
        return len(self.get_node(url).incoming)

    ## outgoing

    def add_outgoing(self, url, children):
        node = self.get_node(url)
        for c_url in children:
            self.add_node(c_url)
            n = self.get_node(c_url)
            node.outgoing[c_url] = n

    def get_iteroutgoing(self, url):
        return (u for u in self.get_node(url).outgoing)

    ## aliases

    def add_ref(self, url, url_alias):
        self.index[url_alias] = self.index[url]
        if not url == url_alias:
            self.get_node(url).aliases.append(url_alias)

    def get_iteraliases(self, url):
        return (a for a in self.get_node(url).aliases)

    def len_aliases(self, url):
        return len(self.get_node(url).aliases)


    ### Service methods

    def dump(self):
        for u in self.get_iterurls():
            io.write_out("%s\n" % u)

    def assert_in_web(self, url):
        if url not in self:
            io.write_err("Url not in the web: %s\n" %
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
        web_root = self.get_root_node()
        paths = [[url]]
        seen[url] = True
        while paths:
            paths_next = []
            for path in paths:
                if self.get_node(path[0]) == web_root:
                    return path
                for url in self.get_iterincoming(path[-1]):
                    if url not in seen:     # loop detected, drop this path
                        seen[url] = True
                        newpath = path[:]   # careful, this is a copy, not ref!
                        newpath.append(url)
                        if self.get_node(url) == web_root:
                            newpath.reverse()
                            return newpath
                        paths_next.append(newpath)
            paths = paths_next

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

class SqliteWeb(Web):
    schema = """
    CREATE TABLE IF NOT EXISTS node (nodeid INTEGER, url TEXT PRIMARY KEY, is_root BOOLEAN);
    CREATE TABLE IF NOT EXISTS node_in  (nodeurl TEXT, linkurl TEXT);
    CREATE TABLE IF NOT EXISTS node_out (nodeurl TEXT, linkurl TEXT);

    CREATE        INDEX IF NOT EXISTS node_id_index   ON node     (nodeid);
    CREATE        INDEX IF NOT EXISTS node_url_index  ON node     (url);
    CREATE        INDEX IF NOT EXISTS node_root_index ON node     (is_root);

    CREATE        INDEX IF NOT EXISTS node_in_node    ON node_in  (nodeurl);
    CREATE        INDEX IF NOT EXISTS node_out_node   ON node_out (nodeurl);

    CREATE UNIQUE INDEX IF NOT EXISTS node_in_index   ON node_in  (nodeurl, linkurl);
    CREATE UNIQUE INDEX IF NOT EXISTS node_out_index  ON node_out (nodeurl, linkurl);
    """

    def __init__(self, file=":memory:", *a, **k):
        Web.__init__(self, *a, **k)

        (base, ext) = os.path.splitext(file)
        if not ext:
            file = file + EXT_SQL
        self.file = file

        self.connect()

    def connect(self):
        self.conn = sqlite3.connect(self.file, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.text_factory = str
        self.cur = self.conn.cursor()

        self.cur.executescript(self.__class__.schema)

    def disconnect(self):
        self.conn.close()

    def db_exec(self, q, *args):
        self.cur.execute(q, *args)

    def db_tuple(self, q, *args):
        self.cur.execute(q, *args)
        res = self.cur.fetchone()
        if res:
            return res

    def db_single(self, q, *args):
        res = self.db_tuple(q, *args)
        if res:
            return res[0]

    def db_iter(self, q, *args):
        self.cur.execute(q, *args)
        res = self.cur.fetchall()
        for r in res:
            yield r[0]

    ## root

    def get_root_node(self):
        res = self.db_tuple('SELECT * FROM node WHERE is_root=?', (True,))
        return Node(res['url'], id=res['nodeid'])

    def get_root(self):
        return self.get_root_node().url

    def set_root(self, url):
        self.add_node(url)
        self.db_exec('UPDATE node SET is_root=?', (False,))
        self.db_exec('UPDATE node SET is_root=? WHERE url=?', (True, url))

    ## index

    def add_node(self, url):
        q = '''INSERT OR IGNORE INTO node VALUES
            (IFNULL((SELECT MAX(nodeid) FROM node),0)+1, ?, ?) '''
        self.db_exec(q, (url, False))

    def get_node(self, url):
        res = self.db_tuple('SELECT * FROM node WHERE url=?', (url,))
        return Node(res['url'], id=res['nodeid'])

    ## index public

    def get_iterurls(self):
        return (u for u in self.db_iter('SELECT url FROM node'))

    def __contains__(self, url):
        return self.db_single('SELECT * FROM node WHERE url=?', (url,))

    def __len__(self):
        return self.db_single('SELECT COUNT (*) FROM node')

    ## incoming

    def add_incoming(self, url, children):
        lst = []
        for c_url in children:
            self.add_node(c_url)
            lst.append((c_url, url))
        q = 'INSERT OR IGNORE INTO node_in VALUES (?, ?)'
        self.cur.executemany(q, lst)

    def get_iterincoming(self, url):
        q = 'SELECT linkurl FROM node_in WHERE nodeurl=?'
        return (u for u in self.db_iter(q, (url,)))

    def len_incoming(self, url):
        q = 'SELECT COUNT(*) FROM node_in WHERE nodeurl=?'
        return self.db_single(q, (url,))

    ## outgoing

    def add_outgoing(self, url, children):
        lst = []
        for c_url in children:
            self.add_node(c_url)
            lst.append((url, c_url))
        q = 'INSERT OR IGNORE INTO node_out VALUES (?, ?)'
        self.cur.executemany(q, lst)

    def get_iteroutgoing(self, url):
        q = 'SELECT linkurl FROM node_out WHERE nodeurl=?'
        return (u for u in self.db_iter(q, (url,)))

    ## aliases

    def add_ref(self, url, url_alias):
        q = '''INSERT OR IGNORE INTO node VALUES
            ((SELECT nodeid FROM node WHERE url=?), ?, ?)'''
        self.db_exec(q, (url, url_alias, False))

    def get_iteraliases(self, url):
        q = 'SELECT url FROM node WHERE nodeid=(SELECT nodeid FROM node WHERE url=?)'
        return (u for u in self.db_iter(q, (url,)))

    def len_aliases(self, url):
        q = '''SELECT COUNT(url) FROM node
            WHERE nodeid=(SELECT nodeid FROM node WHERE url=?)'''
        return self.db_single(q, (url,))


def save_web(wb, filename, dir=None):
    if isinstance(wb, SqliteWeb):
        return
        return wb.disconnect()
    elif isinstance(wb, Web):
        return io.serialize(wb, filename, dir=None)
    raise Exception, "Unknown web type: %s" % type(wb)

def restore_web(filename, dir=None):
    filename = io.p_join(filename, dir)
    if not os.path.exists(filename):
        io.write_fatal("Web file not found: %s\n" % filename)
        sys.exit(1)

    (base, ext) = os.path.splitext(filename)
    if ext == EXT_MEM:
        return io.deserialize(filename, dir=None)
    elif ext == EXT_SQL:
        return SqliteWeb(file=filename)
    io.write_fatal("Failed to restore web from file %s\n" % filename)
    sys.exit(1)



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
    a("--test", action="store_true", help="Run testsuite")
    a("--testmem", action="store_true", help="Run testsuite with in-memory web")
    (opts, args) = io.parse_args(parser)
    try:
        if opts.test or opts.testmem:
            testfile = 'testsuite'

            mem_file = testfile + EXT_MEM
            sql_file = testfile + EXT_SQL
            for f in (mem_file, sql_file):
                if os.path.exists(f):
                    os.unlink(f)

            if opts.test:
                db_file = sql_file
                wb = SqliteWeb(file=db_file)
            else:
                db_file = mem_file
                wb = Web()

            wb.set_root('b')
            wb.set_root('a')
            wb.add_ref('a', 'adupe')
            wb.add_url('a', ['b'])
            wb.add_url('b', ['c'])
            wb.add_url('d', ['e'])      # disconnected from root
            wb.add_incoming('d', 'e')
            wb.add_incoming('e', 'd')   # create loop d <-> e

            io.write_err("Root :  %s\n" % wb.get_root())
            io.write_err("Web  :  %s\n" % wb)
            io.write_err("d.in :  %s\n" % ", ".join(u for u in wb.get_iterincoming('d')))
            io.write_err("e.in :  %s\n" % ", ".join(u for u in wb.get_iterincoming('e')))

            save_web(wb, db_file)
            wb = restore_web(db_file)

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

        wb = restore_web(args[0])
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
