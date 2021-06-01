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

from enum import IntEnum
from io import BytesIO
import logging

import pytest

from trezorlib import protobuf


class SomeEnum(IntEnum):
    Zero = 0
    Five = 5
    TwentyFive = 25


class WiderEnum(IntEnum):
    One = 1
    Two = 2
    Three = 3
    Four = 4
    Five = 5


class NarrowerEnum(IntEnum):
    One = 1
    Five = 5


class PrimitiveMessage(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("uvarint", "uint64"),
        2: protobuf.Field("svarint", "sint64"),
        3: protobuf.Field("bool", "bool"),
        4: protobuf.Field("bytes", "bytes"),
        5: protobuf.Field("unicode", "string"),
        6: protobuf.Field("enum", SomeEnum),
    }


class EnumMessageMoreValues(protobuf.MessageType):
    FIELDS = {1: protobuf.Field("enum", WiderEnum)}


class EnumMessageLessValues(protobuf.MessageType):
    FIELDS = {1: protobuf.Field("enum", NarrowerEnum)}


class RepeatedFields(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("uintlist", "uint64", repeated=True),
        2: protobuf.Field("enumlist", SomeEnum, repeated=True),
        3: protobuf.Field("strlist", "string", repeated=True),
    }


def load_uvarint(buffer):
    reader = BytesIO(buffer)
    return protobuf.load_uvarint(reader)


def dump_uvarint(value):
    writer = BytesIO()
    protobuf.dump_uvarint(writer, value)
    return writer.getvalue()


def load_message(buffer, msg_type):
    reader = BytesIO(buffer)
    return protobuf.load_message(reader, msg_type)


def dump_message(msg):
    writer = BytesIO()
    protobuf.dump_message(writer, msg)
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
    assert protobuf.uint_to_sint(protobuf.sint_to_uint(-(2 ** 32))) == -(2 ** 32)


def test_simple_message():
    msg = PrimitiveMessage(
        uvarint=12345678910,
        svarint=-12345678910,
        bool=True,
        bytes=b"\xDE\xAD\xCA\xFE",
        unicode="Příliš žluťoučký kůň úpěl ďábelské ódy 😊",
        enum=SomeEnum.Five,
    )

    buf = dump_message(msg)
    retr = load_message(buf, PrimitiveMessage)

    assert msg == retr
    assert retr.uvarint == 12345678910
    assert retr.svarint == -12345678910
    assert retr.bool is True
    assert retr.bytes == b"\xDE\xAD\xCA\xFE"
    assert retr.unicode == "Příliš žluťoučký kůň úpěl ďábelské ódy 😊"
    assert retr.enum == SomeEnum.Five
    assert retr.enum == 5


def test_validate_enum(caplog):
    caplog.set_level(logging.INFO)
    # round-trip of a valid value
    msg = EnumMessageMoreValues(enum=WiderEnum.Five)
    buf = dump_message(msg)
    retr = load_message(buf, EnumMessageLessValues)
    assert retr.enum == msg.enum

    assert not caplog.records

    # dumping an invalid enum value fails
    msg.enum = 19
    with pytest.raises(
        ValueError, match="Value 19 in field enum unknown for WiderEnum"
    ):
        dump_message(msg)

    msg.enum = WiderEnum.Three
    buf = dump_message(msg)
    retr = load_message(buf, EnumMessageLessValues)

    assert len(caplog.records) == 1
    record = caplog.records.pop(0)
    assert record.levelname == "INFO"
    assert record.getMessage() == "On field enum: 3 is not a valid NarrowerEnum"
    assert retr.enum == 3


def test_repeated():
    msg = RepeatedFields(
        uintlist=[1, 2, 3], enumlist=[0, 5, 0, 5], strlist=["hello", "world"]
    )
    buf = dump_message(msg)
    retr = load_message(buf, RepeatedFields)

    assert retr == msg


def test_packed():
    values = [4, 44, 444]
    packed_values = b"".join(dump_uvarint(v) for v in values)
    field_id = 1 << 3 | 2  # field number 1, wire type 2
    field_len = len(packed_values)
    message_bytes = dump_uvarint(field_id) + dump_uvarint(field_len) + packed_values

    msg = load_message(message_bytes, RepeatedFields)
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

    msg = load_message(message_bytes, RepeatedFields)
    assert msg
    assert msg.enumlist == values
    assert not msg.uintlist
    assert not msg.strlist


class RequiredFields(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("uvarint", "uint64", required=True),
        2: protobuf.Field("nested", PrimitiveMessage, required=True),
    }


def test_required():
    msg = RequiredFields(uvarint=3, nested=PrimitiveMessage())
    buf = dump_message(msg)
    msg_ok = load_message(buf, RequiredFields)

    assert msg_ok == msg

    with pytest.deprecated_call():
        msg = RequiredFields(uvarint=3)
    with pytest.raises(ValueError):
        # cannot encode instance without the required fields
        dump_message(msg)

    msg = RequiredFields(uvarint=3, nested=None)
    # we can always encode an invalid message
    buf = dump_message(msg)
    with pytest.raises(ValueError):
        # required field `nested` is also not sent
        load_message(buf, RequiredFields)

    msg = RequiredFields(uvarint=None, nested=PrimitiveMessage())
    buf = dump_message(msg)
    with pytest.raises(ValueError):
        # required field `uvarint` is not sent
        load_message(buf, RequiredFields)


class DefaultFields(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("uvarint", "uint32", default=42),
        2: protobuf.Field("svarint", "sint32", default=-42),
        3: protobuf.Field("bool", "bool", default=True),
        4: protobuf.Field("bytes", "bytes", default=b"hello"),
        5: protobuf.Field("unicode", "string", default="hello"),
        6: protobuf.Field("enum", SomeEnum, default=SomeEnum.Five),
    }


def test_default():
    # load empty message
    retr = load_message(b"", DefaultFields)
    assert retr.uvarint == 42
    assert retr.svarint == -42
    assert retr.bool is True
    assert retr.bytes == b"hello"
    assert retr.unicode == "hello"
    assert retr.enum == SomeEnum.Five

    msg = DefaultFields(uvarint=0)
    buf = dump_message(msg)
    retr = load_message(buf, DefaultFields)
    assert retr.uvarint == 0

    msg = DefaultFields(uvarint=None)
    buf = dump_message(msg)
    retr = load_message(buf, DefaultFields)
    assert retr.uvarint == 42
