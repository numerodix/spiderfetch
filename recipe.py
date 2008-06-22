#!/usr/bin/env python


def fill_in_recipe(recipe):
    for rule in recipe:
        if not "depth" in rule:
            rule["depth"] = 1
    return recipe

def load_recipe(filename):
    g, l = {}, {}
    execfile(filename, g, l)
    return fill_in_recipe(l.get("recipe"))

def get_default_recipe():
    recipe = [{"spider": ".*"}]
    recipe = [{"spider": ".*", "dump": ".*"}]
    return fill_in_recipe(recipe)
