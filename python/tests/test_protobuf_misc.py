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

from unittest.mock import patch
from types import SimpleNamespace

import pytest

from trezorlib import protobuf

SimpleEnum = SimpleNamespace(FOO=0, BAR=5, QUUX=13)
SimpleEnumType = protobuf.EnumType("SimpleEnum", (0, 5, 13))

with_simple_enum = patch("trezorlib.messages.SimpleEnum", SimpleEnum, create=True)


class SimpleMessage(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            1: ("uvarint", protobuf.UVarintType, None),
            2: ("svarint", protobuf.SVarintType, None),
            3: ("bool", protobuf.BoolType, None),
            4: ("bytes", protobuf.BytesType, None),
            5: ("unicode", protobuf.UnicodeType, None),
            6: ("enum", SimpleEnumType, None),
            7: ("rep_int", protobuf.UVarintType, protobuf.FLAG_REPEATED),
            8: ("rep_str", protobuf.UnicodeType, protobuf.FLAG_REPEATED),
            9: ("rep_enum", SimpleEnumType, protobuf.FLAG_REPEATED),
        }


class NestedMessage(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            1: ("scalar", protobuf.UVarintType, 0),
            2: ("nested", SimpleMessage, 0),
            3: ("repeated", SimpleMessage, protobuf.FLAG_REPEATED),
        }


class RequiredFields(protobuf.MessageType):
    @classmethod
    def get_fields(cls):
        return {
            1: ("scalar", protobuf.UVarintType, protobuf.FLAG_REQUIRED),
        }


def test_get_field_type():
    # smoke test
    assert SimpleMessage.get_field_type("bool") is protobuf.BoolType

    # full field list
    for fname, ftype, _ in SimpleMessage.get_fields().values():
        assert SimpleMessage.get_field_type(fname) is ftype


@with_simple_enum
def test_enum_to_str():
    # smoke test
    assert SimpleEnumType.to_str(5) == "BAR"

    # full value list
    for name, value in SimpleEnum.__dict__.items():
        assert SimpleEnumType.to_str(value) == name
        assert SimpleEnumType.from_str(name) == value

    with pytest.raises(TypeError):
        SimpleEnumType.from_str("NotAValidValue")

    with pytest.raises(TypeError):
        SimpleEnumType.to_str(999)


@with_simple_enum
def test_dict_roundtrip():
    msg = SimpleMessage(
        uvarint=5,
        svarint=-13,
        bool=False,
        bytes=b"\xca\xfe\x00\xfe",
        unicode="žluťoučký kůň",
        enum=5,
        rep_int=[1, 2, 3],
        rep_str=["a", "b", "c"],
        rep_enum=[0, 5, 13],
    )

    converted = protobuf.to_dict(msg)
    recovered = protobuf.dict_to_proto(SimpleMessage, converted)

    assert recovered == msg


@with_simple_enum
def test_to_dict():
    msg = SimpleMessage(
        uvarint=5,
        svarint=-13,
        bool=False,
        bytes=b"\xca\xfe\x00\xfe",
        unicode="žluťoučký kůň",
        enum=5,
        rep_int=[1, 2, 3],
        rep_str=["a", "b", "c"],
        rep_enum=[0, 5, 13],
    )

    converted = protobuf.to_dict(msg)

    fields = [fname for fname, _, _ in msg.get_fields().values()]
    assert list(sorted(converted.keys())) == list(sorted(fields))

    assert converted["uvarint"] == 5
    assert converted["svarint"] == -13
    assert converted["bool"] is False
    assert converted["bytes"] == "cafe00fe"
    assert converted["unicode"] == "žluťoučký kůň"
    assert converted["enum"] == "BAR"
    assert converted["rep_int"] == [1, 2, 3]
    assert converted["rep_str"] == ["a", "b", "c"]
    assert converted["rep_enum"] == ["FOO", "BAR", "QUUX"]


@with_simple_enum
def test_recover_mismatch():
    dictdata = {
        "bool": True,
        "enum": "FOO",
        "another_field": "hello",
        "rep_enum": ["FOO", 5, 5],
    }
    recovered = protobuf.dict_to_proto(SimpleMessage, dictdata)

    assert recovered.bool is True
    assert recovered.enum is SimpleEnum.FOO
    assert not hasattr(recovered, "another_field")
    assert recovered.rep_enum == [SimpleEnum.FOO, SimpleEnum.BAR, SimpleEnum.BAR]

    for name, _, flags in SimpleMessage.get_fields().values():
        if name not in dictdata:
            if flags == protobuf.FLAG_REPEATED:
                assert getattr(recovered, name) == []
            else:
                assert getattr(recovered, name) is None


@with_simple_enum
def test_hexlify():
    msg = SimpleMessage(bytes=b"\xca\xfe\x00\x12\x34", unicode="žluťoučký kůň")
    converted_nohex = protobuf.to_dict(msg, hexlify_bytes=False)
    converted_hex = protobuf.to_dict(msg, hexlify_bytes=True)

    assert converted_nohex["bytes"] == b"\xca\xfe\x00\x12\x34"
    assert converted_nohex["unicode"] == "žluťoučký kůň"
    assert converted_hex["bytes"] == "cafe001234"
    assert converted_hex["unicode"] == "žluťoučký kůň"

    recovered_nohex = protobuf.dict_to_proto(SimpleMessage, converted_nohex)
    recovered_hex = protobuf.dict_to_proto(SimpleMessage, converted_hex)

    assert recovered_nohex.bytes == msg.bytes
    assert recovered_hex.bytes == msg.bytes


@with_simple_enum
def test_nested_round_trip():
    msg = NestedMessage(
        scalar=9,
        nested=SimpleMessage(uvarint=4, enum=SimpleEnum.FOO),
        repeated=[
            SimpleMessage(),
            SimpleMessage(rep_enum=[SimpleEnum.BAR, SimpleEnum.BAR]),
            SimpleMessage(bytes=b"\xca\xfe"),
        ],
    )

    converted = protobuf.to_dict(msg)
    recovered = protobuf.dict_to_proto(NestedMessage, converted)

    assert msg == recovered


@with_simple_enum
def test_nested_to_dict():
    msg = NestedMessage(
        scalar=9,
        nested=SimpleMessage(uvarint=4, enum=SimpleEnum.FOO),
        repeated=[
            SimpleMessage(),
            SimpleMessage(rep_enum=[SimpleEnum.BAR, SimpleEnum.BAR]),
            SimpleMessage(bytes=b"\xca\xfe"),
        ],
    )

    converted = protobuf.to_dict(msg)
    assert converted["scalar"] == 9
    assert isinstance(converted["nested"], dict)
    assert isinstance(converted["repeated"], list)

    rep = converted["repeated"]
    assert rep[0] == {}
    assert rep[1] == {"rep_enum": ["BAR", "BAR"]}
    assert rep[2] == {"bytes": "cafe"}


@with_simple_enum
def test_nested_recover():
    dictdata = {"nested": {}}
    recovered = protobuf.dict_to_proto(NestedMessage, dictdata)
    assert isinstance(recovered.nested, SimpleMessage)


@with_simple_enum
def test_unknown_enum_to_str():
    simple = SimpleMessage(enum=SimpleEnum.QUUX)
    string = protobuf.format_message(simple)
    assert "enum: QUUX (13)" in string

    simple = SimpleMessage(enum=6000)
    string = protobuf.format_message(simple)
    assert "enum: 6000" in string


@with_simple_enum
def test_unknown_enum_to_dict():
    simple = SimpleMessage(enum=6000)
    converted = protobuf.to_dict(simple)
    assert converted["enum"] == 6000


def test_constructor_deprecations():
    # ok:
    RequiredFields(scalar=0)

    # positional argument
    with pytest.deprecated_call():
        RequiredFields(0)

    # missing required value
    with pytest.deprecated_call():
        RequiredFields()

    # more args than fields
    with pytest.deprecated_call(), pytest.raises(TypeError):
        RequiredFields(0, 0)

    # colliding arg and kwarg
    with pytest.deprecated_call(), pytest.raises(TypeError):
        RequiredFields(0, scalar=0)
