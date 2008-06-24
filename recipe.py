#!/usr/bin/env python

import re
import os

import urlrewrite


def fill_in_recipe(recipe, host_filter_url):
    for rule in recipe:
        if not "depth" in rule:
            rule["depth"] = 1
        rule["host_filter"] = ".*"
        if os.environ.get("HOST_FILTER"):
            rule["host_filter"] = urlrewrite.get_hostname(host_filter_url)
    return recipe

def load_recipe(filename):
    g, l = {}, {}
    execfile(filename, g, l)
    return fill_in_recipe(l.get("recipe"))

def get_default_recipe(host_filter_url):
    #recipe = [{"spider": ".*", "dump": ".*\.jpg", "depth": -1}]
    recipe = [{ "spider": ".*", "dump": "(?i).*\.jpe?g$", "depth": -1 }]
    return fill_in_recipe(recipe, host_filter_url)

def apply_mask(mask, url):
    if mask and url:
        return re.match(mask, url)

def apply_hostfilter(filter_hostname, url):
    if os.environ.get("HOST_FILTER"):
        return urlrewrite.get_hostname(url) == filter_hostname
    return True
