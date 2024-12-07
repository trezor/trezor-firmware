from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def publickey(secret_key: bytes) -> bytes:
    """
    Computes public key from secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def sign(
    secret_key: bytes,
    digest: bytes,
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def verify_publickey(public_key: bytes) -> bool:
    """
    Verifies whether the public key is valid.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_public_key(
    public_key: bytes,
    root_hash: bytes | None = None,
) -> bytes:
    """
    Tweaks the public key with the specified root_hash.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_secret_key(
    secret_key: bytes,
    root_hash: bytes | None = None,
) -> bytes:
    """
    Tweaks the secret key with the specified root_hash.
    """
