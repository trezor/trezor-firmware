from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-optiga.h
def get_certificate(cert_index: int) -> bytes:
    """
    Return the certificate stored at the given index.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-optiga.h
def sign(
    key_index: int,
    digest: bytes,
) -> bytes:
    """
    Uses the private key at key_index to produce a DER-encoded signature of
    the digest.
    """
DEVICE_CERT_INDEX: int
DEVICE_ECC_KEY_INDEX: int
