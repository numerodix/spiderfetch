#!/usr/bin/env python


COLORS = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
HIGHLIGHTS = ["green", "yellow", "cyan", "blue", "magenta", "red"]

color_map = {}
for (n, h) in enumerate(HIGHLIGHTS):
    color_map[n] = [COLORS.index(c) for c in COLORS if h == c].pop()

def map(color):
    return color_map[color % len(HIGHLIGHTS)]

def color_code(color, bold=False):
    bold = (bold == True) and 1 or 0
    if not color:
        return "\033[0m"
    return "\033[%s;3%sm" % (bold, color)
