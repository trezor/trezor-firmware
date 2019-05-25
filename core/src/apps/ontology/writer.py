from apps.common.writers import (  # noqa: F401
    write_bytes,
    write_uint16_le as write_uint16,
    write_uint32_le as write_uint32,
    write_uint64_le as write_uint64,
)
from apps.wallet.sign_tx.writers import write_varint


def write_byte(w: bytearray, n: int) -> None:
    """
    Writes one byte (8bit)
    """
    w.append(n & 0xFF)


def write_bytes_with_length(w: bytearray, buf: bytes) -> None:
    """
    Writes arbitrary byte sequence prepended with the length using variable length integer
    """
    write_varint(w, len(buf))
    write_bytes(w, buf)
