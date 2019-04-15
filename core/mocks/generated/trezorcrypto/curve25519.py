from typing import *

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def generate_secret() -> bytes:
    '''
    Generate secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def publickey(secret_key: bytes) -> bytes:
    '''
    Computes public key from secret key.
    '''

# extmod/modtrezorcrypto/modtrezorcrypto-curve25519.h
def multiply(secret_key: bytes, public_key: bytes) -> bytes:
    '''
    Multiplies point defined by public_key with scalar defined by secret_key.
    Useful for ECDH.
    '''
