try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse
