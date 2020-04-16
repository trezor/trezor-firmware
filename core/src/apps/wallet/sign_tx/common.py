from trezor.crypto import bip32, der
from trezor.crypto.curve import secp256k1


class SigningError(ValueError):
    pass


def ecdsa_sign(node: bip32.HDNode, digest: bytes) -> bytes:
    sig = secp256k1.sign(node.private_key(), digest)
    sigder = der.encode_seq((sig[1:33], sig[33:65]))
    return sigder
