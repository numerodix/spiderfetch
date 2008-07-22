#!/usr/bin/env python

import functools
import hashlib
import os
import random
import sqlite3
import sys
import tempfile
import time

import MySQLdb


schema_drop='drop table node;'
schema_clear='delete from node;'
schema_create='''
create table if not exists node (nodeid integer auto_increment primary key, url text);
'''
schema_create='create table if not exists node (url text)'

def write_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def get_tempfile():
	return tempfile.mkstemp(prefix="."+os.path.basename(sys.argv[0])+".")

class Database(object):
    def __init__(self): pass

    def split_query(self, q):
        for s in q.split(';'):
            if s.strip():
                yield s

    def runinit(self, q):
        for s in self.split_query(q):
            self.cur.execute(s)

    def connect(self, create=False, drop=False, clear=False):
        self.cur = self.conn.cursor()
        if drop:
            self.runinit(schema_drop)
        if create:
            self.runinit(schema_create)
        if clear:
            self.runinit(schema_clear)

    def disconnect(self):
        self.conn.close()

    def fill_query(self, q): pass

class MysqlDatabase(Database):
    def __init__(self, db, user, pw):
        self.db = db
        self.user = user
        self.pw = pw
        write_err("Init MySQL database\n")

    def connect(self, *args, **kw):
        self.conn = MySQLdb.connect(user=self.user, passwd=self.pw, db=self.db)
        Database.connect(self, *args, **kw)

    def fill_query(self, q):
        q = q.replace('insert or ignore', 'insert ignore')
        return q.replace('%%s%%', '%s')

class SqliteDatabase(Database):
    def __init__(self, dbfile):
        self.dbfile = dbfile
        write_err("Init SQLite database on file: %s\n" % self.dbfile)

    def connect(self, *args, **kw):
        self.conn = sqlite3.connect(self.dbfile)
        Database.connect(self, **kw)

    def fill_query(self, q):
        q = q.replace('insert ignore', 'insert or ignore')
        return q.replace('%%s%%', '?')
db = None


def get_list(ln, tuplewrap=False):
    lst = []
    def str_ascii(mi, ma):
        s = ""
        for j in xrange(random.randrange(mi, ma)):
            c = random.randrange(97,123)  # a lowercase letter
            s += chr(c)
        return s
    def integer(bits):
        ceil = 2**bits
        mid = 2**(bits/2)
        return random.randint(mid, ceil)
    def hash_md5(s):
        md5 = hashlib.md5()
        md5.update(s)
        return md5.hexdigest()

    for i in xrange(ln):
        s = str_ascii(20, 150)
        #s = integer(7*8)
        if tuplewrap:
            s = (s,)
        lst.append(s)
    return lst


def timed(tuplewrap=False):
    def wrap(f):
        @functools.wraps(f)
        def new_f(*args, **kw):
            global db
            db.connect()

            ln = args[0]
            lst = get_list(ln, tuplewrap=tuplewrap)

            ts = time.time()
            f(db, lst)
            db.conn.commit()
            dur = time.time() - ts

            db.disconnect()
            return dur
        return new_f
    return wrap


@timed()
def single_synced(db, lst):
    q = db.fill_query('insert or ignore into node values (%%s%%)')
    for s in lst:
        db.cur.execute(q, (s,))
        db.conn.commit()

@timed()
def single_unsynced(db, lst):
    q = db.fill_query('insert or ignore into node values (%%s%%)')
    for s in lst:
        db.cur.execute(q, (s,))

@timed(tuplewrap=True)
def multiple(db, lst):
    q = db.fill_query('insert or ignore into node values (%%s%%)')
    db.cur.executemany(q, lst)

@timed()
def one_transaction(db, lst):
    '''Works in SQLite, unsupported by MySQLdb'''
    ss = "begin;\n"
    for s in lst:
        ss += "insert or ignore into node values ('%s');\n" % s
    ss += "commit;"
    db.cur.executescript(ss)


@timed()
def uniquify(db, lst):
    q = '''
    create table temp (url text);
    insert into temp select distinct * from node;
    drop table node;
    alter table temp rename to node;
    '''
    for s in db.split_query(q):
        db.cur.execute(s)


def collect(f, f_args, repetitions):
    (this_rep, reps) = repetitions
    timestamp = time.strftime('%H:%M', time.localtime())
    write_err("%s  Running %s(%s), %s/%s... " %
              (timestamp, f.__name__, f_args[0], this_rep, reps))
    t = f(*f_args)
    write_err("%s s\n" % t)
    return t

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
        write_err(fmt(f, ffmt(low), ffmt(av), ffmt(high)))

def main():
    records = 10000
    repetitions = 500

    cycle = [
        (multiple, records, 1),
#        (single_unsynced, records, 1),
#        (one_transaction, records, 1),
#        (single_synced, records, 1),
        (uniquify, 0, 10),
    ]
    timings = {}
    
    for rep in xrange(1, repetitions+1):
        for (f, recs, per_rep) in cycle:
            if rep % per_rep == 0:
                t = collect(f, (recs,), (rep, repetitions))
                if f.__name__ not in timings:
                    timings[f.__name__] = []
                timings[f.__name__].append(t)
    
    tuples = []
    for (n, ts) in timings.items():
        av = sum(ts) / len(ts)
        low = min(ts)
        high = max(ts)
        tuples.append((av, low, high, n))
    
    write_conclusion(tuples)
    


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dbfile = sys.argv[1]
    else:
        (fp, dbfile) = get_tempfile()
        os.close(fp)
    db = MysqlDatabase('web', 'root', '')
    #db = SqliteDatabase(dbfile)
    db.connect(create=True, clear=True)

    main()

    if not len(sys.argv) > 1:
        os.unlink(dbfile)
