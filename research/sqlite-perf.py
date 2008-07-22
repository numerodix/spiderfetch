#!/usr/bin/env python

import functools
import os
import random
import sqlite3
import sys
import tempfile
import time


schema='''
create table if not exists node (nodeid integer primary key, url text);
create unique index if not exists idx_url on node (url);
'''
schema='create table if not exists node (nodeid integer primary key, url text);'

def write_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def get_tempfile():
	return tempfile.mkstemp(prefix="."+os.path.basename(sys.argv[0])+".")

def get_list(ln, tuplewrap=False):
    lst = []
    for i in xrange(ln):
        s = ""
        for j in xrange(random.randrange(20, 150)):
            c = random.randrange(97,123)  # a lowercase letter
            s += chr(c)
        if tuplewrap:
            s = (s,)
        lst.append(s)
    return lst

dbfile = None
def timed(tuplewrap=False):
    def wrap(f):
        @functools.wraps(f)
        def new_f(*args, **kw):
            global dbfile
            conn = sqlite3.connect(dbfile)
            cur = conn.cursor()
            cur.executescript(schema)

            ln = args[0]
            lst = get_list(ln, tuplewrap=tuplewrap)

            ts = time.time()
            f(conn, cur, lst)
            conn.commit()
            dur = time.time() - ts

            conn.close()
            return dur
        return new_f
    return wrap


@timed()
def single_synced(conn, cur, lst):
    for s in lst:
        cur.execute('insert into node values (null, ?)', (s,))
        conn.commit()

@timed()
def single_unsynced(conn, cur, lst):
    for s in lst:
        cur.execute('insert into node values (null, ?)', (s,))

@timed(tuplewrap=True)
def multiple(conn, cur, lst):
    cur.executemany('insert into node values (null, ?)', lst)

@timed()
def one_transaction(conn, cur, lst):
    ss = "begin;\n"
    for s in lst:
        ss += "insert into node values (null, '%s');\n" % s
    ss += "commit;"
    cur.executescript(ss)


def collect(f, f_args, execs):
    ts = []
    for i in xrange(execs):
        timestamp = time.strftime('%H:%M', time.localtime())
        write_err("%s  Running %s(%s), %s/%s... " %
                  (timestamp, f.__name__, f_args[0], i+1, execs))
        t = f(*f_args)
        ts.append(t)
        write_err("%s s\n" % t)
    return ts

def write_conclusion(timings):
    timings.sort()
    def ffmt(f):
        s = "%.4f" % f
        if s[0] == '0':
            s = s[1:]
        return s
    def fmt(f, low, av, high):
        return ("%s  %s  %s  %s\n" % 
        (f.ljust(30), low[:12].rjust(12), av[:12].rjust(12), high[:12].rjust(12)))
    write_err('\n')
    write_err(fmt('FUNCTION', 'LOWEST', 'AVERAGE', 'HIGHEST'))
    for (av, low, high, f) in timings:
        write_err(fmt(f.__name__, ffmt(low), ffmt(av), ffmt(high)))

def main():
    records = 10000
    repetitions = 100

    timings = [
        multiple,
#        single_unsynced,
#        one_transaction,
#        single_synced,
    ]
    
    for f in timings:
        ts = collect(f, (records,), repetitions)
        av = sum(ts) / len(ts)
        low = min(ts)
        high = max(ts)
        timings[timings.index(f)] = (av, low, high, f)
    
    write_conclusion(timings)
    


if __name__ == "__main__":
    #global dbfile
    if len(sys.argv) > 1:
        dbfile = sys.argv[1]
    else:
        (fp, dbfile) = get_tempfile()
        os.close(fp)

    main()

    if not len(sys.argv) > 1:
        os.unlink(dbfile)
