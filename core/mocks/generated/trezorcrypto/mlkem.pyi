from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-mlkem.h
def generate_keypair() -> Tuple[bytes, bytes]:
    """
    Returns a tuple of secret key and public key.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-mlkem.h
def encapsulate(encapsulation_key: bytes) -> Tuple[bytes, bytes]:
    """
    Returns a tuple of ciphertext and shared secret.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-mlkem.h
def decapsulate(decapsulation_key: bytes, ciphertext: bytes) -> bytes:
    """
    Returns shared secret.
    """
