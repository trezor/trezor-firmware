# inspired by core/src/trezor/crypto/rlp.py

import typing as t
from collections.abc import Sequence

if t.TYPE_CHECKING:
    RLPItem = t.Union[t.Sequence["RLPItem"], bytes, int]


def _byte_size(x: int) -> int:
    if x < 0:
        raise ValueError("only unsigned ints are supported")
    return (x.bit_length() + 7) // 8


def _int_to_bytes(n: int) -> bytes:
    """Convert to a correctly sized bytes object."""
    return n.to_bytes(_byte_size(n), "big")


def _encode_with_length(value: bytes, header_byte: int) -> bytes:
    length = len(value)
    if length == 1 and value[0] <= 0x7F:
        return value
    elif length <= 55:
        return (header_byte + length).to_bytes(1, "big") + value
    else:
        encoded_length = _int_to_bytes(length)
        return (
            (header_byte + 55 + len(encoded_length)).to_bytes(1, "big")
            + encoded_length
            + value
        )


def encode(value: "RLPItem") -> bytes:
    """Encode lists or objects to bytes."""
    if isinstance(value, int):
        # ints are stored as byte strings
        value = _int_to_bytes(value)

    # sanity check: `str` is a Sequence so it would be incorrectly
    # picked up by the Sequence branch below
    assert not isinstance(value, str)

    # check for bytes type first, because bytes is a Sequence too
    if isinstance(value, bytes):
        header_byte = 0x80
    elif isinstance(value, Sequence):
        header_byte = 0xC0
        value = b"".join(encode(item) for item in value)
    else:
        raise TypeError("Unsupported type")

    return _encode_with_length(value, header_byte)
