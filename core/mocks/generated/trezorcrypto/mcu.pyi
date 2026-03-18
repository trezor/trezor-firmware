from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-mcu.h
def get_certificate() -> bytes:
    """
    Return MCU device certificate.
    """


# upymod/modtrezorcrypto/modtrezorcrypto-mcu.h
def sign(challenge: AnyBytes) -> bytes:
    """
    Sign challenge bytes with MCU device attestation key.
    """
