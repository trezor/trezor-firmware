from trezor.utils import ensure

if False:
    from trezor.utils import Writer


def write_uint8(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFF)
    w.append(n)
    return 1


def write_uint16_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF)
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    return 2


def write_uint16_be(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF)
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
    return 2


def write_uint32_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF)
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    return 4


def write_uint32_be(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
    return 4


def write_uint64_le(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 56) & 0xFF)
    return 8


def write_uint64_be(w: Writer, n: int) -> int:
    ensure(0 <= n <= 0xFFFF_FFFF_FFFF_FFFF)
    w.append((n >> 56) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
    return 8


def write_bytes_unchecked(w: Writer, b: bytes) -> int:
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


def write_bitcoin_varint(w: Writer, n: int) -> None:
    ensure(n >= 0 and n <= 0xFFFF_FFFF)
    if n < 253:
        w.append(n & 0xFF)
    elif n < 0x1_0000:
        w.append(253)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
    else:
        w.append(254)
        w.append(n & 0xFF)
        w.append((n >> 8) & 0xFF)
        w.append((n >> 16) & 0xFF)
        w.append((n >> 24) & 0xFF)


def write_uvarint(w: Writer, n: int) -> None:
    ensure(n >= 0 and n <= 0xFFFF_FFFF_FFFF_FFFF)
    shifted = 1
    while shifted:
        shifted = n >> 7
        byte = (n & 0x7F) | (0x80 if shifted else 0x00)
        w.append(byte)
        n = shifted
