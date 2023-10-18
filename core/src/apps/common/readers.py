from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.utils import BufferReader


def read_compact_size(r: BufferReader) -> int:
    get = r.get  # local_cache_attribute

    prefix = get()
    if prefix < 253:
        n = prefix
    elif prefix == 253:
        n = get()
        n += get() << 8
    elif prefix == 254:
        n = get()
        n += get() << 8
        n += get() << 16
        n += get() << 24
    elif prefix == 255:
        n = get()
        n += get() << 8
        n += get() << 16
        n += get() << 24
        n += get() << 32
        n += get() << 40
        n += get() << 48
        n += get() << 56
    else:
        raise ValueError
    return n


def read_uint16_be(r: BufferReader) -> int:
    data = r.read_memoryview(2)
    return int.from_bytes(data, "big")


def read_uint32_be(r: BufferReader) -> int:
    data = r.read_memoryview(4)
    return int.from_bytes(data, "big")


def read_uint64_be(r: BufferReader) -> int:
    data = r.read_memoryview(8)
    return int.from_bytes(data, "big")


def read_uint16_le(r: BufferReader) -> int:
    data = r.read_memoryview(2)
    return int.from_bytes(data, "little")


def read_uint32_le(r: BufferReader) -> int:
    data = r.read_memoryview(4)
    return int.from_bytes(data, "little")


def read_uint64_le(r: BufferReader) -> int:
    data = r.read_memoryview(8)
    return int.from_bytes(data, "little")
