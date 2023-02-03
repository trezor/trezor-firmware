# generated from definitions_constants.py.mako
# (by running `make templates` in `core`)
# do not edit manually!

from ubinascii import unhexlify

DEFINITIONS_PUBLIC_KEY = b""
MIN_DATA_VERSION = ${ethereum_defs_timestamp}
FORMAT_VERSION = b"trzd1"

if __debug__:
    DEFINITIONS_DEV_PUBLIC_KEY = unhexlify(
        "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d"
    )
