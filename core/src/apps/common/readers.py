from trezor.utils import BufferReader


def read_bitcoin_varint(r: BufferReader) -> int:
    prefix = r.get()
    if prefix < 253:
        n = prefix
    elif prefix == 253:
        n = r.get()
        n += r.get() << 8
    elif prefix == 254:
        n = r.get()
        n += r.get() << 8
        n += r.get() << 16
        n += r.get() << 24
    else:
        raise ValueError
    return n


def read_uint16_be(r: BufferReader) -> int:
    n = r.get()
    return (n << 8) + r.get()


def read_uint32_be(r: BufferReader) -> int:
    n = r.get()
    for _ in range(3):
        n = (n << 8) + r.get()
    return n


def read_uint64_be(r: BufferReader) -> int:
    n = r.get()
    for _ in range(7):
        n = (n << 8) + r.get()
    return n
