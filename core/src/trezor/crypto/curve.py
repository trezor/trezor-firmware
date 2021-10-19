from trezorcrypto import curve25519, ed25519, nist256p1, secp256k1  # noqa: F401

try:
    from trezorcrypto import bip340  # noqa: F401
except ImportError:
    pass
