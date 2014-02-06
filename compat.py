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
