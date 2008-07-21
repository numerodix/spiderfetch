#!/usr/bin/env python

import functools
import os
import random
import sqlite3
import sys
import tempfile
import time


schema='''
create table node (nodeid integer primary key, url text unique)
'''

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

def timed(tuplewrap=False):
    def wrap(f):
        @functools.wraps(f)
        def new_f(*args, **kw):
            (fp, dbfile) = get_tempfile()
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                cur.execute(schema)

                ln = args[0]
                lst = get_list(ln, tuplewrap=tuplewrap)

                ts = time.time()
                f(conn, cur, lst)
                conn.commit()
                dur = time.time() - ts
            finally:
                os.close(fp)
                os.unlink(dbfile)
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
        write_err("Running '%s(%s)', %s/%s... " % (f.__name__, f_args[0], i+1, execs))
        t = f(*f_args)
        ts.append(t)
        write_err("%s s\n" % t)
    return ts

def write_conclusion(timings):
    timings.sort()
    def fmt(f, low, av, high):
        return ("%s  %s  %s  %s\n" % 
        (f.ljust(25), low[:10].rjust(10), av[:10].rjust(10), high[:10].rjust(10)))
    write_err('\n')
    write_err(fmt('FUNCTION', 'LOWEST', 'AVERAGE', 'HIGHEST'))
    for (av, low, high, f) in timings:
        write_err(fmt(f.__name__, str(low), str(av), str(high)))

def main():
    records = 1000
    repetitions = 3

    timings = [
        multiple,
        one_transaction,
        single_unsynced,
        single_synced,
    ]
    
    for f in timings:
        ts = collect(f, (records,), repetitions)
        av = sum(ts) / len(ts)
        low = min(ts)
        high = max(ts)
        timings[timings.index(f)] = (av, low, high, f)
    
    write_conclusion(timings)
    


if __name__ == "__main__":
    main()
