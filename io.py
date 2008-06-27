#!/usr/bin/env python

import gzip
import cPickle as pickle    # cPickle is supposed to be faster
import os
import tempfile
import sys

import shcolor


#LOGDIR = os.environ.get("LOGDIR") or "logs"
LOGDIR = os.environ.get("LOGDIR") or "."

def write_out(s):
    sys.stdout.write(s)

def write_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def write_abort():
    write_err("\n%s\n" % shcolor.color(shcolor.RED, "User aborted"))

def get_tempfile():
	return tempfile.mkstemp(prefix=os.path.basename("." + sys.argv[0]) + ".")

def safe_filename(filename, dir=None):
    if dir:
        filename = os.path.join(dir, filename)
    if os.path.exists(filename):
        path = os.path.dirname(filename)
        file = os.path.basename(filename)
        (root, ext) = os.path.splitext(file)
        serial = 1
        while os.path.exists(filename):
            serial += 1
            filename = os.path.join(path, root + "-" + str(serial) + ext)
    return os.path.basename(filename)

def create_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def file_exists(filename, dir=None):
    if dir:
        filename = os.path.join(dir, filename)
    return os.path.exists(filename)

def delete(filename, dir=None):
    if dir:
        filename = os.path.join(dir, filename)
    return os.unlink(filename)

def savelog(s, filename, mode=None):
    create_dir(LOGDIR)
    mode = mode or 'w'
    open(os.path.join(LOGDIR, filename), mode).write(s)

def serialize(o, filename, dir=None):
    if dir:
        create_dir(dir)
        filename = os.path.join(dir, filename)
    try:
        getattr(o, "_to_pickle")()
    except AttributeError:
        pass
    #fp = gzip.GzipFile(logdir(filename), 'w', compresslevel=1)
    pickle.dump(o, open(filename, 'w'), pickle.HIGHEST_PROTOCOL)

def deserialize(filename, dir=None):
    if dir:
        filename = os.path.join(dir, filename)
    #fp = gzip.GzipFile(filename, 'r')
    o = pickle.load(open(filename, 'r'))
    try:
        getattr(o, "_from_pickle")()
    except AttributeError:
        pass
    return o

def opts_help(option, opt_str, value, parser):
    header = "spiderfetch tool suite\n\n"
    write_err(header+"Usage:  %s %s\n\n" % (os.path.basename(sys.argv[0]), parser.usage))
    for o in parser.option_list:
        var = o.metavar or ""
        short = (o._short_opts and o._short_opts[0]) or ""
        long  = (o._long_opts  and o._long_opts[0])  or ""
        argument = "%s %s %s" % (short, long, var)
        write_err("  %s %s\n" % (argument.strip().ljust(25), o.help))
    sys.exit(2)



if __name__ == "__main__":
    try:
        s = "dvorak"
        (fp, filename) = get_tempfile()
        serialize(s, filename)
        print "Serialization sanity check:", s == deserialize(filename)
    finally:
        os.close(fp)
        os.unlink(filename)
