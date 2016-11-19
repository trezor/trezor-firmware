def int_to_bytes(x: int) -> bytes:
    if x == 0:
        return b''
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
         raise ValueError('Input too long')

def encode(data) -> bytes:
    if isinstance(data, int):
        return encode(int_to_bytes(data))
    if isinstance(data, bytes):
        if len(data) == 1 and ord(data) < 128:
            return data
        else:
            return encode_length(len(data), is_list=False) + data
    elif isinstance(data, list):
        output = b''
        for item in data:
            output += encode(item)
        return encode_length(len(output), is_list=True) + output
    else:
        raise TypeError('Invalid input')
