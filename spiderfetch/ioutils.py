#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

import optparse
import os
import tempfile
import sys

import ansicolor

from spiderfetch.compat import pickle


_help_header = "spiderfetch tool suite\n\n"

_help_tools = """\
== spiderfetch ==

Spiders recursively for urls, starting from <url>. Driven either by <pattern>
or <recipe>. Spidering can be paused/canceled at any time with Ctrl+C, which
will attempt to save the current state in $host.{session,web}. Spidering can
resume provided these two files are found. Terminates either by reaching the
end of the recipe, or reaching the end of the spider queue (no more urls
found). At this point the web is saved to $host.web.

During execution, successful fetches are written to log_urls, failed fetches
to error_urls, and outright errors (that shouldn't happen) to error_log.

== web ==

A query tool for webs that operates on .web files produced by spiderfetch.

== fetch ==

A general purpose fetcher for ftp/http/https, used by spiderfetch. Displays
one url per line and error codes for common fetch errors.

== spider ==

A spider module for spidering urls in documents. Can be used standalone with a
single url to test spidering capabilities and can also highlight matches in the
document.

== dumpstream ==

An automation module for use with mplayer to record media streams. Reads urls
from a file and records with mplayer.
"""

_help_vars = """\
SOCKET_TIMEOUT   Seconds to wait before calling a socket timeout.
TRIES            Number of tries on timeout errors.

ORIG_FILENAMES   Save files with their original filenames on the host (1) or
  use filenames generated from the full url to avoid name collisions (0).
TMPDIR           Temp directory for downloads.
LOGDIR           Directory to use for logfiles.

TERM             When set and not 'dumb' gives color output.
DEBUG_FETCH      Write newlines after every update to see the full output.

VANILLA_USER_AGENT  Don't cloak the user agent.
"""

#LOGDIR = os.environ.get("LOGDIR") or "logs"
LOGDIR = os.environ.get("LOGDIR") or "."

def write_out(s):
    sys.stdout.write(s)

def write_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def write_abort():
    write_err("\n%s\n" % ansicolor.red("User aborted"))

def get_tempfile():
    return tempfile.mkstemp(prefix="." + os.path.basename(sys.argv[0]) + ".")

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
    if dir:
        filename = os.path.basename(filename)
    return filename

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
    try:
        filename_partial = filename + ".partial"
        pickle.dump(o, open(filename_partial, 'wb'), pickle.HIGHEST_PROTOCOL)
        os.rename(filename_partial, filename)
    finally:
        os.path.exists(filename_partial) and os.unlink(filename_partial)

def deserialize(filename, dir=None):
    if dir:
        filename = os.path.join(dir, filename)
    o = pickle.load(open(filename, 'rb'))
    try:
        getattr(o, "_from_pickle")()
    except AttributeError:
        pass
    return o

def init_opts(usage):
    parser = optparse.OptionParser(add_help_option=None)
    parser.usage = usage
    return parser, parser.add_option

def opts_help(option, opt_str, value, parser):
    write_err(_help_header +
              "Usage:  %s %s\n\n" % (os.path.basename(sys.argv[0]), parser.usage))
    for o in parser.option_list:
        var = o.metavar or ""
        short = (o._short_opts and o._short_opts[0]) or ""
        long = (o._long_opts and o._long_opts[0]) or ""
        argument = "%s %s %s" % (short, long, var)
        write_err("  %s %s\n" % (argument.strip().ljust(25), o.help))
    sys.exit(2)

def help_tools(option, opt_str, value, parser):
    write_err(_help_header + _help_tools)
    sys.exit(2)

def help_vars(option, opt_str, value, parser):
    write_err(_help_header + _help_vars)
    sys.exit(2)

def parse_args(parser):
    a = parser.add_option
    a("-h", action="callback", callback=opts_help, help="Display this message")
    a("--tools", action="callback", callback=help_tools, help="Descriptions of the tools")
    a("--vars", action="callback", callback=help_vars, help="Environmental variables")
    (opts, args) = parser.parse_args()
    return opts, args



if __name__ == "__main__":
    try:
        s = "dvorak"
        (fp, filename) = get_tempfile()
        serialize(s, filename)
        print("Serialization sanity check:", s == deserialize(filename))
    finally:
        os.close(fp)
        os.unlink(filename)
