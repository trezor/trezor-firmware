from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-tropic.h
class TropicError(Exception):
    """Error returned by the Tropic Square chip."""


# extmod/modtrezorcrypto/modtrezorcrypto-tropic.h
def ping() -> bool:
    """
    Test the session by pinging the chip.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-tropic.h
def get_certificate() -> bytes:
    """
    Return the chip's certificate.
    """
