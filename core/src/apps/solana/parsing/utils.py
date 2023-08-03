from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def read_compact_u16(reader: BufferReader) -> int:
    """Return the decoded value. BufferReader is advanced by the number of bytes read"""
    value = size = 0
    while size < reader.remaining_count():
        elem = reader.get()
        value |= (elem & 0x7F) << (size * 7)
        size += 1
        if (elem & 0x80) == 0:
            break
    return value


def read_string(data: BufferReader) -> str:
    """
    Reads a string from the buffer. The string is prefixed with its
    length in the first 4 bytes and a 4 byte padding.
    BufferReader is advanced by the number of bytes read.
    """
    length = int.from_bytes(data.read(4), "little")
    # padding
    data.read(4)
    return data.read(length).decode()
