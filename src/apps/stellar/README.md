# Stellar

MAINTAINER = Tomas Susanka <tomas.susanka@satoshilabs.com>

AUTHOR = Tomas Susanka <tomas.susanka@satoshilabs.com>

REVIEWER = Jan Pochyla <jan.pochyla@satoshilabs.com>

-----

TODO

    # Stellar transactions consist of sha256 of:
    # - sha256(network passphrase)
    # - 4-byte unsigned big-endian int type constant (2 for tx)
    # - public key
