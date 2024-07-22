import zlib

CHECKSUM_LENGTH = 4


def compute(data: bytes) -> bytes:
    """
    Returns a CRC-32 checksum of the provided `data`.
    """
    return zlib.crc32(data).to_bytes(CHECKSUM_LENGTH, "big")


def is_valid(checksum: bytes, data: bytes) -> bool:
    """
    Checks whether the CRC-32 checksum of the `data` is the same
    as the checksum provided in `checksum`.
    """
    data_checksum = compute(data)
    return checksum == data_checksum
