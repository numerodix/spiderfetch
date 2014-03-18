# Author: Martin Matusiak <numerodix@gmail.com>
# Licensed under the GNU Public License, version 3.
#
# url: http://github.com/numerodix/pybits


__all__ = ['Colors',
           'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan',
           'white',
           'colorize', 'get_code', 'get_highlighter', 'highlight_string',
           'strip_escapes', 'wrap_string',
           'set_term_title', 'write_out', 'write_err']


import os
import sys

# Don't write escapes to dumb terminals
_disabled = (not os.environ.get("TERM")) or (os.environ.get("TERM") == "dumb")


class Colors(object):
    '''Container class for colors'''
    @classmethod
    def new(cls, colorname):
        try:
            cls.colorlist
        except AttributeError:
            cls.colorlist = []

        newcls = type.__new__(type, colorname, (object,), {})
        newcls.id = len(cls.colorlist)

        cls.colorlist.append(newcls)
        setattr(cls, colorname, newcls)

    @classmethod
    def iter(cls):
        for color in cls.colorlist:
            yield color

## Define Colors members
Colors.new("Black")
Colors.new("Red")
Colors.new("Green")
Colors.new("Yellow")
Colors.new("Blue")
Colors.new("Magenta")
Colors.new("Cyan")
Colors.new("White")

## Define coloring shorthands
def make_func(color):
    def f(s, bold=False, reverse=False):
        return colorize(s, color, bold=bold, reverse=reverse)
    f.__doc__ = "Colorize string with %s" % color.__name__.lower()
    return f

for color in Colors.iter():
    globals()[color.__name__.lower()] = make_func(color)

## Define highlighting colors
highlights = [
    Colors.Green,
    Colors.Yellow,
    Colors.Cyan,
    Colors.Blue,
    Colors.Magenta,
    Colors.Red
]

highlight_map = {}
for (n, h) in enumerate(highlights):
    highlight_map[n] = [color for color in Colors.iter() if h == color].pop()

## Coloring functions
def get_highlighter(colorid):
    '''Map a color index to a highlighting color'''
    return highlight_map[colorid % len(highlights)]

def get_code(color, bold=False, reverse=False):
    '''Return escape code for styling with color, bold or reverse'''
    if _disabled:
        return ""

    fmt = '0;0'
    if bold and reverse:
        fmt = '1;7'
    elif reverse:
        fmt = '0;7'
    elif bold:
        fmt = '0;1'
    color = (color is not None) and ';3%s' % color.id or ''

    return '\033[' + fmt + color + 'm'

def colorize(s, color, bold=False, reverse=False):
    '''Colorize the string'''
    return "%s%s%s" % (get_code(color, bold=bold, reverse=reverse), s, get_code(None))

def wrap_string(s, pos, color, bold=False, reverse=False):
    '''Colorize the string up to a position'''
    if _disabled:
        if pos == 0:
            pos = 1
        return s[:pos - 1] + "|" + s[pos:]

    return "%s%s%s%s" % (get_code(color, bold=bold, reverse=reverse),
                         s[:pos],
                         get_code(None),
                         s[pos:])

def highlight_string(s, *spanlists):
    '''Highlight spans in a string
    @spanlists is on the form [(begin,end)*]*
    Each spanlist gets a new color
    Spans can overlap up to 4 layers
    '''
    # pair span with color and id of the list -> (span, color, list_id)
    tuples = []
    for spanlist in spanlists:
        get_id = lambda spanlist: spanlists.index(spanlist)
        get_color = lambda spanlist: get_highlighter(get_id(spanlist))
        tuples.extend([(span, get_color(spanlist), get_id(spanlist))
                       for span in spanlist])

    # produce list of (pos,color,start_end,list_id) pairs
    # (begin, Red, True, list_id)   # start new color
    # (end, Red, False, list_id)    # end current color
    markers = []
    for i in tuples:
        (begin, end), color, list_id = i
        markers.append((begin, color, True, list_id))
        markers.append((end, color, False, list_id))

    def key(tup):
        pos, color, start_end, list_id = tup
        return pos
    markers.sort(key=key)

    # produce list of (pos, color, layer) pairs
    codes = []
    stack = []
    for (pos, color, start_end, list_id) in markers:
        # stack invariant :  list_id1 < list_id2   =>   i1 < i2
        if start_end:
            inserted = False
            for (i, (c, id)) in enumerate(stack):
                if list_id < id:
                    stack.insert(i, (color, list_id))
                    inserted = True
                    break
            if not inserted:
                stack.append((color, list_id))
        else:
            stack.remove((color, list_id))

        cur_color = None
        if len(stack) > 0:
            (cur_color, _) = stack[-1]

        codes.append((pos, cur_color, len(stack)))

    # apply codes to the string
    cursor = 0
    segments = []
    for (pos, color, layer) in codes:
        bold = False
        reverse = False

        if layer == 2:
            bold = True
        if layer == 3:
            reverse = True
        if layer >= 4:
            bold = True
            reverse = True

        segments.append(s[cursor:pos])
        segments.append(get_code(color, bold=bold, reverse=reverse))

        cursor = pos
    segments.append(s[cursor:])

    return ''.join(segments)

def strip_escapes(s):
    '''Strip escapes from string'''
    import re
    return re.sub('\033[[](?:(?:[0-9]*;)*)(?:[0-9]*m)', '', s)

## Output functions
def set_term_title(s):
    if not _disabled:
        sys.stdout.write("\033]2;%s\007" % s)

def write_to(target, s):
    # assuming we have escapes in the string
    if not _disabled:
        if not os.isatty(target.fileno()):
            s = strip_escapes(s)
    target.write(s)
    target.flush()

def write_out(s):
    '''Write a string to stdout, strip escapes if output is a pipe'''
    write_to(sys.stdout, s)

def write_err(s):
    '''Write a string to stderr, strip escapes if output is a pipe'''
    write_to(sys.stderr, s)


if __name__ == '__main__':
    def test_color():
        width = 10

        lst = []

        lst.extend([[], ['>>> Without colors'], []])
        line = []
        line.append(colorize("Standard".ljust(width),      None))
        line.append(colorize("Bold".ljust(width),          None, bold=True))
        line.append(colorize("Reverse".ljust(width),       None, reverse=True))
        line.append(colorize("Bold & Rev".ljust(width),    None, bold=True, reverse=True))
        lst.append(line)

        lst.extend([[], ['>>> Using colors'], []])
        for color in Colors.iter():
            line = []
            line.append(colorize(color.__name__.ljust(width), color))
            line.append(colorize(color.__name__.ljust(width), color, bold=True))
            line.append(colorize(color.__name__.ljust(width), color, reverse=True))
            line.append(colorize(color.__name__.ljust(width), color, bold=True, reverse=True))
            lst.append(line)

        lst.extend([[], ['>>> Using highlighting colors'], []])
        for color in Colors.iter():
            color = get_highlighter(color.id)
            line = []
            line.append(colorize(color.__name__.ljust(width), color))
            line.append(colorize(color.__name__.ljust(width), color, bold=True))
            line.append(colorize(color.__name__.ljust(width), color, reverse=True))
            line.append(colorize(color.__name__.ljust(width), color, bold=True, reverse=True))
            lst.append(line)

        for line in lst:
            for item in line:
                write_out('%s  ' % item)
            write_out("\n")

    def test_highlight():
        import re
        rxs = [
            '(b+).*\\1',
            '(c+).*\\1',
            '(d+).*\\1',
            '(e+).*\\1',
        ]
        s = """\
aaabbbcccdddeeefffeeedddcccbbbaaa
fffeeedddcccbbbaaabbbcccdddeeefff
"""

        def display(rxs, s):
            spanlists = []
            for rx in rxs:
                spanlist = []
                for m in re.finditer(rx, s):
                    spanlist.append(m.span())
                spanlists.append(spanlist)
            s = highlight_string(s, *spanlists)
            for (i, rx) in enumerate(rxs):
                color = get_highlighter(i)
                color = colorize(color.__name__.ljust(10), color)
                write_out('Regex %s: %s %s\n' % (i, color, rx))
            write_out(s)

        for i in range(0, len(rxs) + 1):
            write_out('\n')
            display(rxs[:i], s)


    try:
        action = sys.argv[1]
    except IndexError:
        print("Usage:  %s [ --color | --highlight ]" % sys.argv[0])
        sys.exit(1)

    if action == '--color':
        test_color()
    elif action == '--highlight':
        test_highlight()
