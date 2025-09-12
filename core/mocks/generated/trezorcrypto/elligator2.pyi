from typing import *
from buffer_types import *


# upymod/modtrezorcrypto/modtrezorcrypto-elligator2.h
def map_to_curve25519(input: AnyBytes) -> bytes:
    """
    Maps a 32-byte input to a curve25519 point.
    """
