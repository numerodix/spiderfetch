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
    line = sys.stdin.readline()
    try:
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
    parser = optparse.OptionParser(add_help_option=None) ; a = parser.add_option
    parser.usage = "< <file>"
    a("-h", action="callback", callback=io.opts_help, help="Display this message")
    (opts, args) = parser.parse_args()
    main()
