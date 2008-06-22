#!/usr/bin/env python

import pickle
import os
import tempfile
import sys


def get_tempfile():
	return tempfile.mkstemp(prefix=os.path.basename(sys.argv[0]) + ".")

def serialize(o, filename):
    pickle.dump(o, open(filename, 'w'), protocol=pickle.HIGHEST_PROTOCOL)
