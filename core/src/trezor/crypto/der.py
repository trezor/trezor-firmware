from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.utils import BufferReader, Writer

# Maximum length of a DER-encoded secp256k1 or secp256p1 signature.
_MAX_DER_SIGNATURE_LENGTH = const(72)

_DER_TAG_SEQUENCE = const(0x30)
_DER_TAG_INTEGER = const(0x02)


def decode_signature(der_signature: AnyBytes) -> bytearray:
    seq = _decode_int_seq(der_signature)
    if len(seq) != 2 or any(len(i) > 32 for i in seq):
        raise ValueError  # invalid or unsupported signature

    signature = bytearray(64)
    signature[32 - len(seq[0]) : 32] = seq[0]
    signature[64 - len(seq[1]) : 64] = seq[1]

    return signature


def encode_signature(signature: AnyBytes) -> AnyBytes:

    if len(signature) not in (64, 65):
        raise ValueError  # invalid or unsupported signature

    offset = 1 if len(signature) == 65 else 0
    r = signature[offset : offset + 32]
    s = signature[offset + 32 : offset + 64]

    return _encode_int_seq(r, s)


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


def _encode_length(len: int) -> bytes:
    if len < 0x80:
        return bytes([len])
    elif len <= 0xFF:
        return bytes([0x81, len])
    elif len <= 0xFFFF:
        return bytes([0x82, len >> 8, len & 0xFF])
    else:
        raise ValueError


def _read_int(r: BufferReader) -> memoryview:
    peek = r.peek  # local_cache_attribute

    if r.get() != _DER_TAG_INTEGER:
        raise ValueError

    n = read_length(r)
    if n == 0:
        raise ValueError

    if peek() & 0x80:
        raise ValueError  # negative integer

    if peek() == 0x00 and n > 1:
        r.get()
        n -= 1
        if peek() & 0x80 == 0x00:
            raise ValueError  # excessive zero-padding

        if peek() == 0x00:
            raise ValueError  # excessive zero-padding

    return r.read_memoryview(n)


def _write_int(w: Writer, number: AnyBytes) -> None:
    i = 0
    while i < len(number) and number[i] == 0:
        i += 1

    length = len(number) - i
    w.append(_DER_TAG_INTEGER)
    if length == 0 or number[i] >= 0x80:
        w.extend(_encode_length(length + 1))
        w.append(0x00)
    else:
        w.extend(_encode_length(length))

    w.extend(memoryview(number)[i:])


def _decode_int_seq(data: AnyBytes) -> list[memoryview]:
    from trezor.utils import BufferReader

    r = BufferReader(data)

    if r.get() != _DER_TAG_SEQUENCE:
        raise ValueError
    n = read_length(r)

    seq = []
    end = r.offset + n
    while r.offset < end:
        i = _read_int(r)
        seq.append(i)

    if r.offset != end or r.remaining_count():
        raise ValueError

    return seq


def _encode_int_seq(
    *seq: AnyBytes, buffer_preallocate_len: int = _MAX_DER_SIGNATURE_LENGTH
) -> AnyBytes:
    from trezor.utils import empty_bytearray

    buffer = empty_bytearray(buffer_preallocate_len)
    buffer.append(_DER_TAG_SEQUENCE)
    for i in seq:
        _write_int(buffer, i)
    buffer[1:1] = _encode_length(len(buffer) - 1)
    return buffer
