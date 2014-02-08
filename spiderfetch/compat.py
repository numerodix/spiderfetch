try:
    import cPickle as pickle
except ImportError:
    import pickle  # noqa

try:
    import httplib
except ImportError:
    from http import client as httplib  # noqa

try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse  # noqa


try:
    from urllib import FancyURLopener
except ImportError:
    from urllib.request import FancyURLopener  # noqa

try:
    from urllib import ContentTooShortError
except ImportError:
    from urllib.request import ContentTooShortError  # noqa

try:
    from urllib import ftpwrapper
except ImportError:
    from urllib.request import ftpwrapper  # noqa

try:
    from urllib import splittype
except ImportError:
    from urllib.request import splittype  # noqa

try:
    from urllib import unwrap
except ImportError:
    from urllib.request import unwrap  # noqa
