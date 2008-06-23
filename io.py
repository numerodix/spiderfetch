#!/usr/bin/env python

import gzip
import pickle
import os
import tempfile
import sys

import shcolor


def write_out(s):
    sys.stdout.write(s)

def write_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def write_abort():
    write_err("\n%s\n" % shcolor.color(shcolor.RED, "User aborted"))

def get_tempfile():
	return tempfile.mkstemp(prefix=os.path.basename("." + sys.argv[0]) + ".")

def serialize(o, filename):
    fp = gzip.GzipFile(filename, 'w')
    pickle.dump(o, fp, protocol=pickle.HIGHEST_PROTOCOL)

def deserialize(filename):
    fp = gzip.GzipFile(filename, 'r')
    return pickle.load(fp)

def opts_help(option, opt_str, value, parser):
    print "Usage: %s [options]" % sys.argv[0]
    for o in parser.option_list:
        var = o.metavar or ""
        short = (o._short_opts and o._short_opts[0]) or ""
        long = (o._long_opts and o._long_opts[0]) or ""
        argument = "%s %s %s" % (short, long, var)
        write_err("  %s %s\n" % (argument.strip().ljust(25), o.help))
    sys.exit(0)

if __name__ == "__main__":
    try:
        s = "dvorak"
        (fp, filename) = get_tempfile()
        serialize(s, filename)
        print s == deserialize(filename)
    finally:
        os.close(fp)
        os.unlink(filename)
