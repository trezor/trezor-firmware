from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base_types import Reader, Writer

_UINT_BUFFER = bytearray(1)


def dump_uint(writer: Writer, n: int, width: int) -> None:
    """
    Constant-width integer serialization
    """
    buffer = _UINT_BUFFER
    for _ in range(width):
        buffer[0] = n & 0xFF
        writer.write(buffer)
        n >>= 8


def uvarint_size(n: int) -> int:
    """
    Returns size in bytes n would occupy serialized as varint
    """
    bts = 0 if n != 0 else 1
    while n:
        n >>= 7
        bts += 1
    return bts


def dump_uvarint_b(n: int) -> bytearray:
    """
    Serializes uvarint to the buffer
    """
    buffer = bytearray(uvarint_size(n))
    return dump_uvarint_b_into(n, buffer, 0)


def dump_uvarint_b_into(n: int, buffer: bytearray, offset: int = 0) -> bytearray:
    """
    Serializes n as variable size integer to the provided buffer.
    """
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[offset] = (n & 0x7F) | (0x80 if shifted else 0x00)
        offset += 1
        n = shifted
    return buffer


def load_uvarint(reader: Reader) -> int:
    buffer = _UINT_BUFFER
    result = 0
    shift = 0
    byte = 0x80
    while byte & 0x80:
        reader.readinto(buffer)
        byte = buffer[0]
        result += (byte & 0x7F) << shift
        shift += 7
    return result


def dump_uvarint(writer: Writer, n: int) -> None:
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    buffer = _UINT_BUFFER
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        writer.write(buffer)
        n = shifted
