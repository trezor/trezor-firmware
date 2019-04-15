_UINT_BUFFER = bytearray(1)


def load_uint(reader, width):
    """
    Constant-width integer serialization
    """
    buffer = _UINT_BUFFER
    result = 0
    shift = 0
    for _ in range(width):
        reader.readinto(buffer)
        result += buffer[0] << shift
        shift += 8
    return result


def dump_uint(writer, n, width):
    """
    Constant-width integer serialization
    """
    buffer = _UINT_BUFFER
    for _ in range(width):
        buffer[0] = n & 0xFF
        writer.write(buffer)
        n >>= 8


def uvarint_size(n):
    """
    Returns size in bytes n would occupy serialized as varint
    """
    bts = 0 if n != 0 else 1
    while n:
        n >>= 7
        bts += 1
    return bts


def load_uvarint_b(buffer):
    """
    Variable int deserialization, synchronous from buffer.
    """
    result = 0
    idx = 0
    byte = 0x80
    while byte & 0x80:
        byte = buffer[idx]
        result += (byte & 0x7F) << (7 * idx)
        idx += 1
    return result


def dump_uvarint_b(n):
    """
    Serializes uvarint to the buffer
    """
    buffer = bytearray(uvarint_size(n))
    return dump_uvarint_b_into(n, buffer, 0)


def dump_uvarint_b_into(n, buffer, offset=0):
    """
    Serializes n as variable size integer to the provided buffer.
    """
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[offset] = (n & 0x7F) | (0x80 if shifted else 0x00)
        offset += 1
        n = shifted
    return buffer


def dump_uint_b_into(n, width, buffer, offset=0):
    """
    Serializes fixed size integer to the buffer
    """
    for idx in range(width):
        buffer[idx + offset] = n & 0xFF
        n >>= 8
    return buffer


def load_uvarint(reader):
    buffer = _UINT_BUFFER
    result = 0
    shift = 0
    byte = 0x80
    while byte & 0x80:
        reader.readinto(buffer)
        byte = buffer[0]
        result += (byte & 0x7F) << shift
        shift += 7
    return result


def dump_uvarint(writer, n):
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    buffer = _UINT_BUFFER
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        writer.write(buffer)
        n = shifted
