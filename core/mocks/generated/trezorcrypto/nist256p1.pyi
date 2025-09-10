from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def generate_secret() -> bytes:
    """
    Generate secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def publickey(secret_key: AnyBytes, compressed: bool = True) -> bytes:
    """
    Computes public key from secret key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def sign(
    secret_key: AnyBytes, digest: AnyBytes, compressed: bool = True
) -> bytes:
    """
    Uses secret key to produce the signature of the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify(public_key: AnyBytes, signature: AnyBytes, digest: AnyBytes) -> bool:
    """
    Uses public key to verify the signature of the digest.
    Returns True on success.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify_recover(signature: AnyBytes, digest: AnyBytes) -> bytes:
    """
    Uses signature of the digest to verify the digest and recover the public
    key. Returns public key on success, None if the signature is invalid.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def multiply(secret_key: AnyBytes, public_key: AnyBytes) -> bytes:
    """
    Multiplies point defined by public_key with scalar defined by
    secret_key. Useful for ECDH.
    """
