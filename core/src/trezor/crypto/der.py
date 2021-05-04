from micropython import const

from trezor.utils import BufferReader, empty_bytearray

if False:
    from trezor.utils import Writer

# Maximum length of a DER-encoded secp256k1 or secp256p1 signature.
MAX_DER_SIGNATURE_LENGTH = const(72)


def encode_length(l: int) -> bytes:
    if l < 0x80:
        return bytes([l])
    elif l <= 0xFF:
        return bytes([0x81, l])
    elif l <= 0xFFFF:
        return bytes([0x82, l >> 8, l & 0xFF])
    else:
        raise ValueError


def read_length(r: BufferReader) -> int:
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


def write_int(w: Writer, number: bytes) -> None:
    i = 0
    while i < len(number) and number[i] == 0:
        i += 1

    length = len(number) - i
    w.append(0x02)
    if length == 0 or number[i] >= 0x80:
        w.extend(encode_length(length + 1))
        w.append(0x00)
    else:
        w.extend(encode_length(length))

    w.extend(memoryview(number)[i:])


def read_int(r: BufferReader) -> memoryview:
    if r.get() != 0x02:
        raise ValueError

    n = read_length(r)
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

    return r.read_memoryview(n)


def encode_seq(seq: tuple) -> bytes:
    # Preallocate space for a signature, which is all that this function ever encodes.
    buffer = empty_bytearray(MAX_DER_SIGNATURE_LENGTH)
    buffer.append(0x30)
    for i in seq:
        write_int(buffer, i)
    buffer[1:1] = encode_length(len(buffer) - 1)
    return buffer


def decode_seq(data: memoryview) -> list[memoryview]:
    r = BufferReader(data)

    if r.get() != 0x30:
        raise ValueError
    n = read_length(r)

    seq = []
    end = r.offset + n
    while r.offset < end:
        i = read_int(r)
        seq.append(i)

    if r.offset != end or r.remaining_count():
        raise ValueError

    return seq
