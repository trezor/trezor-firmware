# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from io import BytesIO

import pytest

from trezorlib import protobuf


class PrimitiveMessage(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            0: ("uvarint", protobuf.UVarintType, 0),
            1: ("svarint", protobuf.SVarintType, 0),
            2: ("bool", protobuf.BoolType, 0),
            3: ("bytes", protobuf.BytesType, 0),
            4: ("unicode", protobuf.UnicodeType, 0),
        }


def load_uvarint(buffer):
    reader = BytesIO(buffer)
    return protobuf.load_uvarint(reader)


def dump_uvarint(value):
    writer = BytesIO()
    protobuf.dump_uvarint(writer, value)
    return writer.getvalue()


def test_dump_uvarint():
    assert dump_uvarint(0) == b"\x00"
    assert dump_uvarint(1) == b"\x01"
    assert dump_uvarint(0xFF) == b"\xff\x01"
    assert dump_uvarint(123456) == b"\xc0\xc4\x07"

    with pytest.raises(ValueError):
        dump_uvarint(-1)


def test_load_uvarint():
    assert load_uvarint(b"\x00") == 0
    assert load_uvarint(b"\x01") == 1
    assert load_uvarint(b"\xff\x01") == 0xFF
    assert load_uvarint(b"\xc0\xc4\x07") == 123456


def test_sint_uint():
    """
    Protobuf interleaved signed encoding
    https://developers.google.com/protocol-buffers/docs/encoding#structure
    LSbit is sign, rest is shifted absolute value.
    Or, by example, you count like so: 0, -1, 1, -2, 2, -3 ...
    """
    assert protobuf.sint_to_uint(0) == 0
    assert protobuf.uint_to_sint(0) == 0

    assert protobuf.sint_to_uint(-1) == 1
    assert protobuf.sint_to_uint(1) == 2

    assert protobuf.uint_to_sint(1) == -1
    assert protobuf.uint_to_sint(2) == 1

    # roundtrip:
    assert protobuf.uint_to_sint(protobuf.sint_to_uint(1234567891011)) == 1234567891011
    assert protobuf.uint_to_sint(protobuf.sint_to_uint(-2 ** 32)) == -2 ** 32


def test_simple_message():
    msg = PrimitiveMessage(
        uvarint=12345678910,
        svarint=-12345678910,
        bool=True,
        bytes=b"\xDE\xAD\xCA\xFE",
        unicode="Příliš žluťoučký kůň úpěl ďábelské ódy 😊",
    )

    buf = BytesIO()

    protobuf.dump_message(buf, msg)
    buf.seek(0)
    retr = protobuf.load_message(buf, PrimitiveMessage)

    assert msg == retr
    assert retr.uvarint == 12345678910
    assert retr.svarint == -12345678910
    assert retr.bool is True
    assert retr.bytes == b"\xDE\xAD\xCA\xFE"
    assert retr.unicode == "Příliš žluťoučký kůň úpěl ďábelské ódy 😊"
