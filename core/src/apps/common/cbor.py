"""
Minimalistic CBOR implementation, supports only what we need in cardano.
"""

import ustruct as struct
from micropython import const

from trezor import log, utils

from . import readers

if False:
    from typing import Any, Union, Iterator, Tuple

    Value = Any
    CborSequence = Union[list[Value], Tuple[Value, ...]]

_CBOR_TYPE_MASK = const(0xE0)
_CBOR_INFO_BITS = const(0x1F)

_CBOR_UNSIGNED_INT = const(0b000 << 5)
_CBOR_NEGATIVE_INT = const(0b001 << 5)
_CBOR_BYTE_STRING = const(0b010 << 5)
_CBOR_TEXT_STRING = const(0b011 << 5)
_CBOR_ARRAY = const(0b100 << 5)
_CBOR_MAP = const(0b101 << 5)
_CBOR_TAG = const(0b110 << 5)
_CBOR_PRIMITIVE = const(0b111 << 5)

_CBOR_UINT8_FOLLOWS = const(0x18)
_CBOR_UINT16_FOLLOWS = const(0x19)
_CBOR_UINT32_FOLLOWS = const(0x1A)
_CBOR_UINT64_FOLLOWS = const(0x1B)
_CBOR_VAR_FOLLOWS = const(0x1F)

_CBOR_FALSE = const(0x14)
_CBOR_TRUE = const(0x15)
_CBOR_NULL = const(0x16)
_CBOR_BREAK = const(0x1F)
_CBOR_RAW_TAG = const(0x18)


def _header(typ: int, l: int) -> bytes:
    if l < 24:
        return struct.pack(">B", typ + l)
    elif l < 2 ** 8:
        return struct.pack(">BB", typ + 24, l)
    elif l < 2 ** 16:
        return struct.pack(">BH", typ + 25, l)
    elif l < 2 ** 32:
        return struct.pack(">BI", typ + 26, l)
    elif l < 2 ** 64:
        return struct.pack(">BQ", typ + 27, l)
    else:
        raise NotImplementedError("Length %d not suppported" % l)


def _cbor_encode(value: Value) -> Iterator[bytes]:
    if isinstance(value, int):
        if value >= 0:
            yield _header(_CBOR_UNSIGNED_INT, value)
        else:
            yield _header(_CBOR_NEGATIVE_INT, -1 - value)
    elif isinstance(value, bytes):
        yield _header(_CBOR_BYTE_STRING, len(value))
        yield value
    elif isinstance(value, bytearray):
        yield _header(_CBOR_BYTE_STRING, len(value))
        yield bytes(value)
    elif isinstance(value, str):
        encoded_value = value.encode()
        yield _header(_CBOR_TEXT_STRING, len(encoded_value))
        yield encoded_value
    elif isinstance(value, list) or isinstance(value, tuple):
        # definite-length valued list
        yield _header(_CBOR_ARRAY, len(value))
        for x in value:
            yield from _cbor_encode(x)
    elif isinstance(value, dict):
        yield _header(_CBOR_MAP, len(value))
        sorted_map = sorted((encode(k), v) for k, v in value.items())
        for k, v in sorted_map:
            yield k
            yield from _cbor_encode(v)
    elif isinstance(value, Tagged):
        yield _header(_CBOR_TAG, value.tag)
        yield from _cbor_encode(value.value)
    elif isinstance(value, IndefiniteLengthArray):
        yield bytes([_CBOR_ARRAY + 31])
        for x in value.array:
            yield from _cbor_encode(x)
        yield bytes([_CBOR_PRIMITIVE + 31])
    elif isinstance(value, bool):
        if value:
            yield bytes([_CBOR_PRIMITIVE + _CBOR_TRUE])
        else:
            yield bytes([_CBOR_PRIMITIVE + _CBOR_FALSE])
    elif isinstance(value, Raw):
        yield value.value
    elif value is None:
        yield bytes([_CBOR_PRIMITIVE + _CBOR_NULL])
    else:
        if __debug__:
            log.debug(__name__, "not implemented (encode): %s", type(value))
        raise NotImplementedError


def _read_length(r: utils.BufferReader, aux: int) -> int:
    if aux < _CBOR_UINT8_FOLLOWS:
        return aux
    elif aux == _CBOR_UINT8_FOLLOWS:
        return r.get()
    elif aux == _CBOR_UINT16_FOLLOWS:
        return readers.read_uint16_be(r)
    elif aux == _CBOR_UINT32_FOLLOWS:
        return readers.read_uint32_be(r)
    elif aux == _CBOR_UINT64_FOLLOWS:
        return readers.read_uint64_be(r)
    else:
        raise NotImplementedError("Length %d not suppported" % aux)


def _cbor_decode(r: utils.BufferReader) -> Value:
    fb = r.get()
    fb_type = fb & _CBOR_TYPE_MASK
    fb_aux = fb & _CBOR_INFO_BITS
    if fb_type == _CBOR_UNSIGNED_INT:
        return _read_length(r, fb_aux)
    elif fb_type == _CBOR_NEGATIVE_INT:
        val = _read_length(r, fb_aux)
        return -1 - val
    elif fb_type == _CBOR_BYTE_STRING:
        ln = _read_length(r, fb_aux)
        return r.read(ln)
    elif fb_type == _CBOR_TEXT_STRING:
        ln = _read_length(r, fb_aux)
        return r.read(ln).decode()
    elif fb_type == _CBOR_ARRAY:
        if fb_aux == _CBOR_VAR_FOLLOWS:
            res: Value = []
            while True:
                item = _cbor_decode(r)
                if item == _CBOR_PRIMITIVE + _CBOR_BREAK:
                    break
                res.append(item)
            return res
        else:
            ln = _read_length(r, fb_aux)
            res = []
            for _ in range(ln):
                item = _cbor_decode(r)
                res.append(item)
            return res
    elif fb_type == _CBOR_MAP:
        res = {}
        if fb_aux == _CBOR_VAR_FOLLOWS:
            while True:
                key = _cbor_decode(r)
                if key in res:
                    raise ValueError
                if key == _CBOR_PRIMITIVE + _CBOR_BREAK:
                    break
                value = _cbor_decode(r)
                res[key] = value
        else:
            ln = _read_length(r, fb_aux)
            for _ in range(ln):
                key = _cbor_decode(r)
                if key in res:
                    raise ValueError
                value = _cbor_decode(r)
                res[key] = value
        return res
    elif fb_type == _CBOR_TAG:
        val = _read_length(r, fb_aux)
        item = _cbor_decode(r)
        if val == _CBOR_RAW_TAG:  # only tag 24 (0x18) is supported
            return item
        else:
            return Tagged(val, item)
    elif fb_type == _CBOR_PRIMITIVE:
        if fb_aux == _CBOR_FALSE:
            return False
        elif fb_aux == _CBOR_TRUE:
            return True
        elif fb_aux == _CBOR_NULL:
            return None
        elif fb_aux == _CBOR_BREAK:
            return fb
        else:
            raise NotImplementedError
    else:
        if __debug__:
            log.debug(__name__, "not implemented (decode): %s", fb)
        raise NotImplementedError


class Tagged:
    def __init__(self, tag: int, value: Value) -> None:
        self.tag = tag
        self.value = value

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Tagged)
            and self.tag == other.tag
            and self.value == other.value
        )


class Raw:
    def __init__(self, value: Value):
        self.value = value


class IndefiniteLengthArray:
    def __init__(self, array: list[Value]) -> None:
        self.array = array

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IndefiniteLengthArray):
            return self.array == other.array
        elif isinstance(other, list):
            return self.array == other
        else:
            return False


def encode(value: Value) -> bytes:
    return b"".join(_cbor_encode(value))


def encode_streamed(value: Value) -> Iterator[bytes]:
    """
    Returns the encoded value as an iterable of the individual
    CBOR "chunks", removing the need to reserve a continuous
    chunk of memory for the full serialized representation of the value
    """
    return _cbor_encode(value)


def encode_chunked(value: Value, max_chunk_size: int) -> Iterator[bytes]:
    """
    Returns the encoded value as an iterable of chunks of a given size,
    removing the need to reserve a continuous chunk of memory for the
    full serialized representation of the value.
    """
    if max_chunk_size <= 0:
        raise ValueError

    chunks = encode_streamed(value)

    chunk_buffer = utils.empty_bytearray(max_chunk_size)
    try:
        current_chunk_view = utils.BufferReader(next(chunks))
        while True:
            num_bytes_to_write = min(
                current_chunk_view.remaining_count(),
                max_chunk_size - len(chunk_buffer),
            )
            chunk_buffer.extend(current_chunk_view.read(num_bytes_to_write))

            if len(chunk_buffer) >= max_chunk_size:
                yield chunk_buffer
                chunk_buffer[:] = bytes()

            if current_chunk_view.remaining_count() == 0:
                current_chunk_view = utils.BufferReader(next(chunks))
    except StopIteration:
        if len(chunk_buffer) > 0:
            yield chunk_buffer


def decode(cbor: bytes) -> Value:
    r = utils.BufferReader(cbor)
    res = _cbor_decode(r)
    if r.remaining_count():
        raise ValueError
    return res
