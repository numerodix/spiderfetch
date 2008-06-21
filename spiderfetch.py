#!/usr/bin/env python

import os
import sys
import tempfile

import fetch
import filetype
import spider
import urlrewrite


url = sys.argv[1]

queue = [url]
depth = 0
while queue:
    print "\nDepth: %s\nQueue: %s\n" % (depth, len(queue))

    working_set = queue
    queue = []
    depth += 1

    for url in working_set: 
        try:
            (_, filename) = tempfile.mkstemp(prefix=sys.argv[0] + ".")
            fetch.spider(url, filename)
            data = open(filename, 'r').read()

            urls = spider.unbox_it_to_ss(spider.findall(data))
            urls = urlrewrite.rewrite_urls(url, urls)

            queue.extend(urls)
        except KeyboardInterrupt:
            fetch.write_abort()
            sys.exit(1)
        except fetch.ChangedUrlWarning, e:
            queue.append(e.new_url)
        except IOError:
            print "url failed: %s" % url
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    if queue:
        queue = urlrewrite.unique(queue)

