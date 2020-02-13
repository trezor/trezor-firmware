# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
import logging

import pytest

from trezorlib import protobuf


class PrimitiveMessage(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            1: ("uvarint", protobuf.UVarintType, 0),
            2: ("svarint", protobuf.SVarintType, 0),
            3: ("bool", protobuf.BoolType, 0),
            4: ("bytes", protobuf.BytesType, 0),
            5: ("unicode", protobuf.UnicodeType, 0),
            6: ("enum", protobuf.EnumType("t", (0, 5, 25)), 0),
        }


class EnumMessageMoreValues(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {1: ("enum", protobuf.EnumType("t", (0, 1, 2, 3, 4, 5)), 0)}


class EnumMessageLessValues(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {1: ("enum", protobuf.EnumType("t", (0, 5)), 0)}


class RepeatedFields(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            1: ("uintlist", protobuf.UVarintType, protobuf.FLAG_REPEATED),
            2: ("enumlist", protobuf.EnumType("t", (0, 1)), protobuf.FLAG_REPEATED),
            3: ("strlist", protobuf.UnicodeType, protobuf.FLAG_REPEATED),
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
    assert load_uvarint(b"\x80\x80\x80\x80\x00") == 0


def test_broken_uvarint():
    with pytest.raises(IOError):
        load_uvarint(b"\x80\x80")


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
        enum=5,
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
    assert retr.enum == 5


def test_validate_enum(caplog):
    caplog.set_level(logging.INFO)
    # round-trip of a valid value
    msg = EnumMessageMoreValues(enum=0)
    buf = BytesIO()
    protobuf.dump_message(buf, msg)
    buf.seek(0)
    retr = protobuf.load_message(buf, EnumMessageLessValues)
    assert retr.enum == msg.enum

    assert not caplog.records

    # dumping an invalid enum value fails
    msg.enum = 19
    buf.seek(0)
    protobuf.dump_message(buf, msg)

    assert len(caplog.records) == 1
    record = caplog.records.pop(0)
    assert record.levelname == "INFO"
    assert record.getMessage() == "Value 19 unknown for type t"

    msg.enum = 3
    buf.seek(0)
    protobuf.dump_message(buf, msg)
    buf.seek(0)
    protobuf.load_message(buf, EnumMessageLessValues)

    assert len(caplog.records) == 1
    record = caplog.records.pop(0)
    assert record.levelname == "INFO"
    assert record.getMessage() == "Value 3 unknown for type t"


def test_repeated():
    msg = RepeatedFields(
        uintlist=[1, 2, 3], enumlist=[0, 1, 0, 1], strlist=["hello", "world"]
    )
    buf = BytesIO()
    protobuf.dump_message(buf, msg)
    buf.seek(0)
    retr = protobuf.load_message(buf, RepeatedFields)

    assert retr == msg


def test_enum_in_repeated(caplog):
    caplog.set_level(logging.INFO)

    msg = RepeatedFields(enumlist=[0, 1, 2, 3])
    buf = BytesIO()
    protobuf.dump_message(buf, msg)
    assert len(caplog.records) == 2
    for record in caplog.records:
        assert record.levelname == "INFO"
        assert "unknown for type t" in record.getMessage()


def test_packed():
    values = [4, 44, 444]
    packed_values = b"".join(dump_uvarint(v) for v in values)
    field_id = 1 << 3 | 2  # field number 1, wire type 2
    field_len = len(packed_values)
    message_bytes = dump_uvarint(field_id) + dump_uvarint(field_len) + packed_values

    buf = BytesIO(message_bytes)
    msg = protobuf.load_message(buf, RepeatedFields)
    assert msg
    assert msg.uintlist == values
    assert not msg.enumlist
    assert not msg.strlist


def test_packed_enum():
    values = [0, 0, 0, 0]
    packed_values = b"".join(dump_uvarint(v) for v in values)
    field_id = 2 << 3 | 2  # field number 2, wire type 2
    field_len = len(packed_values)
    message_bytes = dump_uvarint(field_id) + dump_uvarint(field_len) + packed_values

    buf = BytesIO(message_bytes)
    msg = protobuf.load_message(buf, RepeatedFields)
    assert msg
    assert msg.enumlist == values
    assert not msg.uintlist
    assert not msg.strlist
