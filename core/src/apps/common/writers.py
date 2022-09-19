from typing import TYPE_CHECKING

from trezor.utils import ensure

if TYPE_CHECKING:
    from trezor.utils import Writer


def _write_uint(w: Writer, n: int, bits: int, bigendian: bool) -> int:
    ensure(0 <= n <= 2**bits - 1, "overflow")
    shifts = range(0, bits, 8)
    if bigendian:
        shifts = reversed(shifts)
    for num in shifts:
        w.append((n >> num) & 0xFF)
    return bits // 8


def write_uint8(w: Writer, n: int) -> int:
    return _write_uint(w, n, 8, False)


def write_uint16_le(w: Writer, n: int) -> int:
    return _write_uint(w, n, 16, False)


def write_uint32_le(w: Writer, n: int) -> int:
    return _write_uint(w, n, 32, False)


def write_uint32_be(w: Writer, n: int) -> int:
    return _write_uint(w, n, 32, True)


def write_uint64_le(w: Writer, n: int) -> int:
    return _write_uint(w, n, 64, False)


def write_uint64_be(w: Writer, n: int) -> int:
    return _write_uint(w, n, 64, True)


def write_bytes_unchecked(w: Writer, b: bytes | memoryview) -> int:
    w.extend(b)
    return len(b)


def write_bytes_fixed(w: Writer, b: bytes, length: int) -> int:
    ensure(len(b) == length)
    w.extend(b)
    return length


def write_bytes_reversed(w: Writer, b: bytes, length: int) -> int:
    ensure(len(b) == length)
    w.extend(bytes(reversed(b)))
    return length


def write_compact_size(w: Writer, n: int) -> None:
    ensure(0 <= n <= 0xFFFF_FFFF)
    append = w.append  # local_cache_attribute

    if n < 253:
        append(n & 0xFF)
    elif n < 0x1_0000:
        append(253)
        write_uint16_le(w, n)
    elif n < 0x1_0000_0000:
        append(254)
        write_uint32_le(w, n)
    else:
        append(255)
        write_uint64_le(w, n)


def write_uvarint(w: Writer, n: int) -> None:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)
    shifted = 1
    while shifted:
        shifted = n >> 7
        byte = (n & 0x7F) | (0x80 if shifted else 0x00)
        w.append(byte)
        n = shifted
