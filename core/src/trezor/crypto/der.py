def encode_length(l: int) -> bytes:
    if l < 0x80:
        return bytes([l])
    elif l <= 0xFF:
        return bytes([0x81, l])
    elif l <= 0xFFFF:
        return bytes([0x82, l & 0xFF, l >> 8])
    else:
        raise ValueError


def encode_int(i: bytes) -> bytes:
    i = i.lstrip(b"\x00")
    if i[0] >= 0x80:
        i = b"\x00" + i
    return b"\x02" + encode_length(len(i)) + i


def encode_seq(seq: tuple) -> bytes:
    res = b""
    for i in seq:
        res += encode_int(i)
    return b"\x30" + encode_length(len(res)) + res
