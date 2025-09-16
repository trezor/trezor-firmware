from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def publickey(secret_key: AnyBytes) -> bytes:
    """
    Computes public key from secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def sign(
    secret_key: AnyBytes,
    digest: AnyBytes,
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def verify_publickey(public_key: AnyBytes) -> bool:
    """
    Verifies whether the public key is valid.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def verify(public_key: AnyBytes, signature: AnyBytes, digest: AnyBytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_public_key(
    public_key: AnyBytes,
    root_hash: AnyBytes | None = None,
) -> bytes:
    """
    Tweaks the public key with the specified root_hash.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-bip340.h
def tweak_secret_key(
    secret_key: AnyBytes,
    root_hash: AnyBytes | None = None,
) -> bytes:
    """
    Tweaks the secret key with the specified root_hash.
    """
