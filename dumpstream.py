#!/usr/bin/env python

import optparse
import os
import subprocess
import sys
import traceback

import io



def logerror(path):
    io.savelog("Path failed: %s\n" % path, "error_dumpstream")

def main():
    try:
        line = sys.stdin.readline()
        while line:
            path = line.strip()
            filename = os.path.basename(path)
            args = ["mplayer", "-dumpstream", "-dumpfile", filename, path]
            retval = subprocess.call(args)
            if retval:
                logerror(path)

            line = sys.stdin.readline()
    except KeyboardInterrupt:
        io.write_abort()
    except Exception, e:
        s  = "%s\n" % traceback.format_exc()
        s += "%s\n" % str(e)
        s += "Invocation string: %s\n" % str(args)
        io.write_err(s)



if __name__ == "__main__":
    (parser, a) = io.init_opts("< <file>")
    (opts, args) = io.parse_args(parser)
    main()
