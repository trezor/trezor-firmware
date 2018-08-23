def empty_bytearray(preallocate: int) -> bytearray:
    """
    Returns bytearray that won't allocate for at least `preallocate` bytes.
    Useful in case you want to avoid allocating too often.
    """
    b = bytearray(preallocate)
    b[:] = bytes()
    return b


def write_uint8(w: bytearray, n: int) -> int:
    assert 0 <= n <= 0xFF
    w.append(n)
    return 1


def write_uint32_le(w: bytearray, n: int) -> int:
    assert 0 <= n <= 0xFFFFFFFF
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    return 4


def write_uint32_be(w: bytearray, n: int) -> int:
    assert 0 <= n <= 0xFFFFFFFF
    w.append((n >> 24) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
    return 4


def write_uint64_le(w: bytearray, n: int) -> int:
    assert 0 <= n <= 0xFFFFFFFFFFFFFFFF
    w.append(n & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 56) & 0xFF)
    return 8


def write_uint64_be(w: bytearray, n: int) -> int:
    assert 0 <= n <= 0xFFFFFFFFFFFFFFFF
    w.append((n >> 56) & 0xFF)
    w.append((n >> 48) & 0xFF)
    w.append((n >> 40) & 0xFF)
    w.append((n >> 32) & 0xFF)
    w.append((n >> 24) & 0xFF)
    w.append((n >> 16) & 0xFF)
    w.append((n >> 8) & 0xFF)
    w.append(n & 0xFF)
    return 8


def write_bytes(w: bytearray, b: bytes) -> int:
    w.extend(b)
    return len(b)


def write_bytes_reversed(w: bytearray, b: bytes) -> int:
    w.extend(bytes(reversed(b)))
    return len(b)
