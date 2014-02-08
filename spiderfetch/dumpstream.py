#!/usr/bin/env python

import os
import subprocess
import sys
import traceback

from spiderfetch import ioutils



def logerror(path):
    ioutils.savelog("Path failed: %s\n" % path, "error_dumpstream")

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
        ioutils.write_abort()
    except Exception as e:
        s = "%s\n" % traceback.format_exc()
        s += "%s\n" % str(e)
        s += "Invocation string: %s\n" % str(args)
        ioutils.write_err(s)



if __name__ == "__main__":
    (parser, a) = ioutils.init_opts("< <file>")
    (opts, args) = ioutils.parse_args(parser)
    main()
