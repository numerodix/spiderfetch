#!/usr/bin/env python

from __future__ import absolute_import

import re
import os

from spiderfetch import urlrewrite


RECIPEDIR = os.environ.get("RECIPEDIR") or "recipes"

class PatternError(Exception):
    pass


def switch_key(d, k1, k2):
    if d.get(k1):
        d[k2] = d[k1]
        del d[k1]
        return d

def rewrite_recipe(recipe, url):
    for rule in recipe:
        if not "depth" in rule:
            rule["depth"] = 1
        if os.environ.get("DEPTH"):
            rule["depth"] = int(os.environ.get("DEPTH"))

        if os.environ.get("HOST_FILTER"):
            rule["host_filter"] = urlrewrite.get_hostname(url)
        if os.environ.get("FETCH_ALL"):
            switch_key(rule, "dump", "fetch")
        elif os.environ.get("DUMP_ALL"):
            switch_key(rule, "fetch", "dump")

        # compile regexes
        for r in ("dump", "fetch", "spider"):
            if r in rule and type(rule[r]) == str:
                try:
                    rule[r] = re.compile(rule[r])
                except re.error as e:
                    raise PatternError("Pattern error: %s: %s" % (e.args[0], rule[r]))
    return recipe

def overrule_records(records):
    if os.environ.get("FETCH_ALL") or os.environ.get("DUMP_ALL"):
        for record in records:
            if os.environ.get("FETCH_ALL"):
                switch_key(record, "dump", "fetch")
            elif os.environ.get("DUMP_ALL"):
                switch_key(record, "fetch", "dump")
    return records

def load_recipe(filename, url):
    (root, ext) = os.path.splitext(filename)
    if not ext:
        ext = ".py"
    filename = root + ext
    if not os.path.exists(filename):    # try $PWD first
        path = os.path.dirname(__file__)
        filename = os.path.join(path, RECIPEDIR, filename)
    g, l = {}, {}
    execfile(filename, g, l)
    return rewrite_recipe(l.get("recipe"), url)

def get_recipe(pattern, url):
    recipe = [{"spider": ".*", "fetch": pattern}]
    return rewrite_recipe(recipe, url)

def get_queue(url, mode=None):
    return [{"mode": mode, "url": url}]

def apply_mask(pattern, url):
    if pattern and url:
        return re.search(pattern, url)

def apply_hostfilter(filter_hostname, url):
    if os.environ.get("HOST_FILTER"):
        return urlrewrite.get_hostname(url) == filter_hostname
    return True
