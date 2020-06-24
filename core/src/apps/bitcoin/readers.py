from apps.common.readers import BytearrayReader, read_bitcoin_varint


def read_bytes_prefixed(r: BytearrayReader) -> bytes:
    n = read_bitcoin_varint(r)
    return r.read(n)


def read_op_push(r: BytearrayReader) -> int:
    prefix = r.get()
    if prefix < 0x4C:
        n = prefix
    elif prefix == 0x4C:
        n = r.get()
    elif prefix == 0x4D:
        n = r.get()
        n += r.get() << 8
    elif prefix == 0x4E:
        n = r.get()
        n += r.get() << 8
        n += r.get() << 16
        n += r.get() << 24
    else:
        raise ValueError
    return n
