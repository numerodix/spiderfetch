try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import httplib
except ImportError:
    from http import client as httplib

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse

try:
    from urllib import ftpwrapper
except ImportError:
    from urllib.request import ftpwrapper

try:
    from urllib import FancyURLopener
except ImportError:
    from urllib.request import FancyURLopener

try:
    from urllib import unwrap
except ImportError:
    from urllib.request import unwrap
