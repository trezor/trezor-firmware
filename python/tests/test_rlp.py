import pytest

from trezorlib import _rlp

VECTORS = (  # data, expected
    (b"\x10", b"\x10"),
    (b"dog", b"\x83dog"),
    (b"A" * 55, b"\xb7" + b"A" * 55),
    (b"A" * 56, b"\xb8\x38" + b"A" * 56),
    (b"A" * 1024, b"\xb9\x04\x00" + b"A" * 1024),
    ([b"dog", b"cat", [b"spy"]], b"\xcd\x83dog\x83cat\xc4\x83spy"),
    ([b"A" * 1024], b"\xf9\x04\x03\xb9\x04\x00" + b"A" * 1024),
    ([], b"\xc0"),
    ([b"A"] * 55, b"\xf7" + b"A" * 55),
    ([b"A"] * 56, b"\xf8\x38" + b"A" * 56),
    ([b"A"] * 1024, b"\xf9\x04\x00" + b"A" * 1024),
    ([b"dog"] * 1024, b"\xf9\x10\x00" + b"\x83dog" * 1024),
    (b"", b"\x80"),
    (1, b"\x01"),
    (0x7F, b"\x7f"),
    (0x80, b"\x81\x80"),
    (0x1_0000_0001, b"\x85\x01\x00\x00\x00\x01"),
    (2 ** (54 * 8), b"\xb7\x01" + b"\x00" * 54),
    (2 ** (55 * 8), b"\xb8\x38\x01" + b"\x00" * 55),
    ([0x1234, 0x5678], b"\xc6\x82\x12\x34\x82\x56\x78"),
)


@pytest.mark.parametrize("data, expected", VECTORS)
def test_encode(data: "_rlp.RLPItem", expected: bytes):
    actual = _rlp.encode(data)
    assert len(actual) == len(expected)
    assert actual == expected
