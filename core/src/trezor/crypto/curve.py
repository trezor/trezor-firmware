from trezor import utils
from trezorcrypto import curve25519, ed25519, nist256p1, secp256k1  # noqa: F401

if not utils.BITCOIN_ONLY:
    from trezorcrypto import secp256k1_zkp, curve25519_axolotl  # noqa: F401
