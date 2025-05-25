from micropython import const

from trezor import utils
from trezor.crypto import crc

CHECKSUM_LENGTH = const(4)


def compute(data: bytes | utils.BufferType, crc_chain: int = 0) -> bytes:
    """
    Returns a CRC-32 checksum of the provided `data`. Allows for for chaining
    computations over multiple data segments using `crc_chain` (optional).
    """
    return crc.crc32(data, crc_chain).to_bytes(CHECKSUM_LENGTH, "big")


def compute_int(data: bytes | utils.BufferType, crc_chain: int = 0) -> int:
    """
    Returns a CRC-32 checksum of the provided `data`. Allows for for chaining
    computations over multiple data segments using `crc_chain` (optional).

    Returns checksum in the form of `int`.
    """
    return crc.crc32(data, crc_chain)


def is_valid(checksum: bytes | utils.BufferType, data: bytes) -> bool:
    """
    Checks whether the CRC-32 checksum of the `data` is the same
    as the checksum provided in `checksum`.
    """
    data_checksum = compute(data)
    return checksum == data_checksum
