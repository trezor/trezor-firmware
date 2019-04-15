from typing import *

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def publickey(secret_key: bytes, compressed: bool = True) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def sign(secret_key: bytes, digest: bytes, compressed: bool = True) -> bytes:
    '''
    Uses secret key to produce the signature of the digest.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
    '''
    Uses public key to verify the signature of the digest.
    Returns True on success.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def verify_recover(signature: bytes, digest: bytes) -> bytes:
    '''
    Uses signature of the digest to verify the digest and recover the public key.
    Returns public key on success, None on failure.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-nist256p1.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key.
    Useful for ECDH.
    '''
