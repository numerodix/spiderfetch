#!/usr/bin/env python

import os
import pickle
import sys
import tempfile
import traceback

import fetch
import filetype
import spider
import urlrewrite
import web


url = sys.argv[1]
web = web.Web()
web.add_url(url, [])

queue = web.urls()
depth = 0
while queue:
    print "\nDepth: %s\nQueue: %s\n" % (depth, len(queue))

    working_set = queue
    queue = []
    depth += 1
    
    for url in working_set: 
        try:
            (fp, filename) = tempfile.mkstemp(prefix=sys.argv[0] + ".")
            fetch.spider(url, filename)
            data = open(filename, 'r').read()

            urls = spider.unbox_it_to_ss(spider.findall(data))
            urls = urlrewrite.rewrite_urls(url, urls)

            for u in urls:
                if u not in web:
                    queue.append(u)
                    web.add_url(url, [u])

        except fetch.ChangedUrlWarning, e:
            web.add_ref(url, e.new_url)
            queue.append(e.new_url)
        except KeyboardInterrupt:
            #pickle.dump(web, open('web', 'w'), protocol=pickle.HIGHEST_PROTOCOL)
            sys.exit(1)
        except IOError, e:
            s = traceback.format_exc()
            s += "\nbad url:   |%s|\n" % url
            node = web.get(url)
            for u in node.incoming.keys():
                s += "ref    :   |%s|\n" % u
            s += "\n"
            open("error_log", "a").write(s)
        finally:
            if filename and os.path.exists(filename):
                os.unlink(filename)
            try:
                os.close(fp)
            except:
                pass
