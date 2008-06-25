#!/usr/bin/env python

import re
import os

import urlrewrite


class PatternError(Exception): pass

def switch_key(d, k1, k2):
    if d.get(k1):
        d[k2] = d[k1]
        del d[k1]
        return d

def rewrite_recipe(recipe, url):
    for rule in recipe:
        if not "depth" in rule:
            rule["depth"] = 1
        if os.environ.get("HOST_FILTER"):
            rule["host_filter"] = urlrewrite.get_hostname(url)
        if os.environ.get("FETCH_ALL"):
            switch_key(rule, "dump", "fetch")
        elif os.environ.get("DUMP_ALL"):
            switch_key(rule, "fetch", "dump")
    return recipe

def overrule_records(records):
    for record in records:
        if os.environ.get("FETCH_ALL"):
            switch_key(record, "dump", "fetch")
        elif os.environ.get("DUMP_ALL"):
            switch_key(record, "fetch", "dump")
    return records

def load_recipe(filename):
    g, l = {}, {}
    execfile(filename, g, l)
    return fill_in_recipe(l.get("recipe"))

def get_recipe(url, pattern):
    #recipe = [{"spider": ".*", "dump": ".*\.jpg", "depth": -1}]
    #recipe = [{ "spider": ".*", "fetch": "(?i).*\.jpe?g$", "depth": -1 }]
    #recipe = [{ "spider": ".*", "dump": "(?i).*\.jpe?g$", "depth": -1 }]
    #recipe = [{ "spider": ".*", "depth": -1 }]
    try:
        pattern = re.compile(pattern)
    except re.error, e:
        raise PatternError, "Pattern error: %s: %s" % (e.args[0], pattern)
    recipe = [{ "spider": ".*", "fetch": pattern }]
    return rewrite_recipe(recipe, url)

def get_queue(url):
    return [{"spider": True, "url": url}]

def apply_mask(pattern, url):
    if pattern and url:
        return re.match(pattern, url)

def apply_hostfilter(filter_hostname, url):
    if os.environ.get("HOST_FILTER"):
        return urlrewrite.get_hostname(url) == filter_hostname
    return True
