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



if __name__ == "__main__":
    try:
        s = "dvorak"
        (fp, filename) = get_tempfile()
        serialize(s, filename)
        print s == deserialize(filename)
    finally:
        os.close(fp)
        os.unlink(filename)
