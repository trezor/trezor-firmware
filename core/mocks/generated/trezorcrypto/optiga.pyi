from typing import *


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
class OptigaError(Exception):
    """Error returned by the Optiga chip."""


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
class SigningInaccessible(OptigaError):
    """The signing key is inaccessible.
    Typically, this will happen after the bootloader has been unlocked.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
def get_certificate(cert_index: int) -> bytes:
    """
    Return the certificate stored at the given index.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
def sign(
    key_index: int,
    digest: bytes,
) -> bytes:
    """
    Uses the private key at key_index to produce a DER-encoded signature of
    the digest.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
def get_sec() -> int | None:
    """
    Returns the value of Optiga's security event counter.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-optiga.h
def set_sec_max() -> None:
    """
    Set Optiga's security event counter to maximum.
    """
DEVICE_CERT_INDEX: int
DEVICE_ECC_KEY_INDEX: int
