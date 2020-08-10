"""
Minimalistic CBOR implementation, supports only what we need in cardano.
"""

import ustruct as struct
from micropython import const

from trezor import log

if False:
    from typing import Any, Iterable, List, Tuple

    Value = Any

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


def _cbor_encode(value: Value) -> Iterable[bytes]:
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


def _read_length(cbor: bytes, aux: int) -> Tuple[int, bytes]:
    if aux < _CBOR_UINT8_FOLLOWS:
        return (aux, cbor)
    elif aux == _CBOR_UINT8_FOLLOWS:
        return (cbor[0], cbor[1:])
    elif aux == _CBOR_UINT16_FOLLOWS:
        res = cbor[1]
        res += cbor[0] << 8
        return (res, cbor[2:])
    elif aux == _CBOR_UINT32_FOLLOWS:
        res = cbor[3]
        res += cbor[2] << 8
        res += cbor[1] << 16
        res += cbor[0] << 24
        return (res, cbor[4:])
    elif aux == _CBOR_UINT64_FOLLOWS:
        res = cbor[7]
        res += cbor[6] << 8
        res += cbor[5] << 16
        res += cbor[4] << 24
        res += cbor[3] << 32
        res += cbor[2] << 40
        res += cbor[1] << 48
        res += cbor[0] << 56
        return (res, cbor[8:])
    else:
        raise NotImplementedError("Length %d not suppported" % aux)


def _cbor_decode(cbor: bytes) -> Tuple[Value, bytes]:
    fb = cbor[0]
    data = b""
    fb_type = fb & _CBOR_TYPE_MASK
    fb_aux = fb & _CBOR_INFO_BITS
    if fb_type == _CBOR_UNSIGNED_INT:
        return _read_length(cbor[1:], fb_aux)
    elif fb_type == _CBOR_NEGATIVE_INT:
        val, data = _read_length(cbor[1:], fb_aux)
        return (-1 - val, data)
    elif fb_type == _CBOR_BYTE_STRING:
        ln, data = _read_length(cbor[1:], fb_aux)
        return (data[0:ln], data[ln:])
    elif fb_type == _CBOR_TEXT_STRING:
        ln, data = _read_length(cbor[1:], fb_aux)
        return (data[0:ln].decode(), data[ln:])
    elif fb_type == _CBOR_ARRAY:
        if fb_aux == _CBOR_VAR_FOLLOWS:
            res = []  # type: Value
            data = cbor[1:]
            while True:
                item, data = _cbor_decode(data)
                if item == _CBOR_PRIMITIVE + _CBOR_BREAK:
                    break
                res.append(item)
            return (res, data)
        else:
            ln, data = _read_length(cbor[1:], fb_aux)
            res = []
            for i in range(ln):
                item, data = _cbor_decode(data)
                res.append(item)
            return (res, data)
    elif fb_type == _CBOR_MAP:
        res = {}
        if fb_aux == _CBOR_VAR_FOLLOWS:
            data = cbor[1:]
            while True:
                key, data = _cbor_decode(data)
                if key in res:
                    raise ValueError
                if key == _CBOR_PRIMITIVE + _CBOR_BREAK:
                    break
                value, data = _cbor_decode(data)
                res[key] = value
        else:
            ln, data = _read_length(cbor[1:], fb_aux)
            for i in range(ln):
                key, data = _cbor_decode(data)
                if key in res:
                    raise ValueError
                value, data = _cbor_decode(data)
                res[key] = value
        return res, data
    elif fb_type == _CBOR_TAG:
        val, data = _read_length(cbor[1:], fb_aux)
        item, data = _cbor_decode(data)
        if val == _CBOR_RAW_TAG:  # only tag 24 (0x18) is supported
            return item, data
        else:
            return Tagged(val, item), data
    elif fb_type == _CBOR_PRIMITIVE:
        if fb_aux == _CBOR_FALSE:
            return (False, cbor[1:])
        elif fb_aux == _CBOR_TRUE:
            return (True, cbor[1:])
        elif fb_aux == _CBOR_NULL:
            return (None, cbor[1:])
        elif fb_aux == _CBOR_BREAK:
            return (cbor[0], cbor[1:])
        else:
            raise NotImplementedError
    else:
        if __debug__:
            log.debug(__name__, "not implemented (decode): %s", cbor[0])
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
    def __init__(self, array: List[Value]) -> None:
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


def decode(cbor: bytes) -> Value:
    res, check = _cbor_decode(cbor)
    if not (check == b""):
        raise ValueError
    return res
