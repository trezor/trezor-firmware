from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-crc.h
def crc32(data: bytes, crc: int = 0) -> int:
    """
    Computes a CRC32 checksum of `data`.

    Args:
        `data` (`bytes`): Input data.
        `crc` (`int`, `optional`): Initial CRC value for chaining
        computations over multiple data segments. Defaults to 0.

    Returns:
        `int`: Computed CRC32 checksum.
    """
