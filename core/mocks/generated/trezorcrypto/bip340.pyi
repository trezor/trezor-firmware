from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def publickey(secret_key: bytes) -> bytes:
    """
    Computes public key from secret key.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def sign(
    secret_key: bytes,
    digest: bytes,
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_public_key(
    public_key: bytes,
    root_hash: bytes | None = None,
) -> bytes:
    """
    Tweaks the public key with the specified root_hash.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_secret_key(
    secret_key: bytes,
    root_hash: bytes | None = None,
) -> bytes:
    """
    Tweaks the secret key with the specified root_hash.
    """
