#!/usr/bin/env python

import os


_disable = "TERM" in os.environ and os.environ["TERM"] == "dumb"

BLACK = 0
RED = 1
GREEN = 2
YELLOW = 3
BLUE = 4
MAGENTA = 5
CYAN = 6
WHITE = 7

COLORS = [BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE]
HIGHLIGHTS = [GREEN, YELLOW, CYAN, BLUE, MAGENTA, RED]

color_map = {}
for (n, h) in enumerate(HIGHLIGHTS):
    color_map[n] = [COLORS.index(c) for c in COLORS if h == c].pop()

def map(color):
    return color_map[color % len(HIGHLIGHTS)]

def code(color, bold=False, reverse=False):
    if _disable:
        return ""

    bold = (bold == True) and 1 or 0
    if reverse:
        return "\033[7m"
    if not color:
        return "\033[0m"
    return "\033[%s;3%sm" % (bold, color)

def color(color, s):
    if _disable: 
        return s
    return "\033[0;3%sm%s\033[0m" % (color, s)

def wrap_s(s, pos, color, bold=False, reverse=False):
    if _disable:
        if pos == 0: pos = 1
        return s[:pos-1] + "|" + s[pos:]

    return code(color, bold=bold, reverse=reverse) + s[:pos] + code(None) + s[pos:]
