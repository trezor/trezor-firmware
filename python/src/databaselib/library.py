# pylint: skip-file

try:
    from trezor.crypto.hashlib import sha256  # NOQA
except ImportError:
    pass

try:
    from hashlib import sha256  # NOQA
except ImportError:
    pass

try:
    from json import dumps, loads  # NOQA
except ImportError:
    pass

try:
    from ujson import dumps, loads  # NOQA
except ImportError:
    pass

from binascii import hexlify, unhexlify  # NOQA
