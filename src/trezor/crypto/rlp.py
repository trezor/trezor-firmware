def to_binary(x: int):
    if x == 0:
        return b''
    r = bytearray()
    while x:
        r.append(x % 256)
        x //= 256
    return bytes(reversed(r))

def encode_length(l, offset):
    if l < 56:
         return bytes([l + offset])
    elif l < 256 ** 8:
         bl = to_binary(l)
         return bytes([len(bl) + offset + 55]) + bl
    else:
         raise ValueError('Input too long')

def encode(data):
    if isinstance(data, int):
        return encode(to_binary(data))
    if isinstance(data, bytes):
        if len(data) == 1 and ord(data) < 128:
            return data
        else:
            return encode_length(len(data), 128) + data
    elif isinstance(data, list):
        output = b''
        for item in data:
            output += encode(item)
        return encode_length(len(output), 192) + output
    else:
        raise TypeError('Invalid input')
