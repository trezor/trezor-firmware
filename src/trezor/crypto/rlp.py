def int_to_bytes(x: int) -> bytes:
    if x == 0:
        return b""
    r = bytearray()
    while x:
        r.append(x % 256)
        x //= 256
    return bytes(reversed(r))


def encode_length(l: int, is_list: bool) -> bytes:
    offset = 0xC0 if is_list else 0x80
    if l < 56:
        return bytes([l + offset])
    elif l < 256 ** 8:
        bl = int_to_bytes(l)
        return bytes([len(bl) + offset + 55]) + bl
    else:
        raise ValueError("Input too long")


def encode(data, include_length=True) -> bytes:
    if isinstance(data, int):
        data = int_to_bytes(data)
    if isinstance(data, bytearray):
        data = bytes(data)
    if isinstance(data, bytes):
        if (len(data) == 1 and ord(data) < 128) or not include_length:
            return data
        else:
            return encode_length(len(data), is_list=False) + data
    elif isinstance(data, list):
        output = b""
        for item in data:
            output += encode(item)
        if include_length:
            return encode_length(len(output), is_list=True) + output
        else:
            return output
    else:
        raise TypeError("Invalid input of type " + str(type(data)))


def field_length(length: int, first_byte: bytearray) -> int:
    if length == 1 and first_byte[0] <= 0x7f:
        return 1
    elif length <= 55:
        return 1 + length
    elif length <= 0xff:
        return 2 + length
    elif length <= 0xffff:
        return 3 + length
    return 4 + length
