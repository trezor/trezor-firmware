from trezor.crypto.hashlib import blake256, ripemd160, sha256


def sha256_ripemd160_digest(b: bytes) -> bytes:
    h = sha256(b).digest()
    h = ripemd160(h).digest()
    return h


def blake256_ripemd160_digest(b: bytes) -> bytes:
    h = blake256(b).digest()
    h = ripemd160(h).digest()
    return h
