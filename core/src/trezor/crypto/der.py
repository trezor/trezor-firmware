from trezor.utils import BufferReader

if False:
    from typing import List


def encode_length(l: int) -> bytes:
    if l < 0x80:
        return bytes([l])
    elif l <= 0xFF:
        return bytes([0x81, l])
    elif l <= 0xFFFF:
        return bytes([0x82, l >> 8, l & 0xFF])
    else:
        raise ValueError


def decode_length(r: BufferReader) -> int:
    init = r.get()
    if init < 0x80:
        # short form encodes length in initial octet
        return init

    if init == 0x80 or init == 0xFF or r.peek() == 0x00:
        raise ValueError  # indefinite length, RFU or not shortest possible

    # long form
    n = 0
    for _ in range(init & 0x7F):
        n = n * 0x100 + r.get()

    if n < 128:
        raise ValueError  # encoding is not the shortest possible

    return n


def encode_int(i: bytes) -> bytes:
    i = i.lstrip(b"\x00")
    if not i:
        i = b"\00"

    if i[0] >= 0x80:
        i = b"\x00" + i
    return b"\x02" + encode_length(len(i)) + i


def decode_int(r: BufferReader) -> bytes:
    if r.get() != 0x02:
        raise ValueError

    n = decode_length(r)
    if n == 0:
        raise ValueError

    if r.peek() & 0x80:
        raise ValueError  # negative integer

    if r.peek() == 0x00 and n > 1:
        r.get()
        n -= 1
        if r.peek() & 0x80 == 0x00:
            raise ValueError  # excessive zero-padding

        if r.peek() == 0x00:
            raise ValueError  # excessive zero-padding

    return r.read(n)


def encode_seq(seq: tuple) -> bytes:
    res = b""
    for i in seq:
        res += encode_int(i)
    return b"\x30" + encode_length(len(res)) + res


def decode_seq(data: bytes) -> List[bytes]:
    r = BufferReader(data)

    if r.get() != 0x30:
        raise ValueError
    n = decode_length(r)

    seq = []
    end = r.offset + n
    while r.offset < end:
        i = decode_int(r)
        seq.append(i)

    if r.offset != end or r.remaining_count():
        raise ValueError

    return seq
