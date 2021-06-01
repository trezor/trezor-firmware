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

import pytest

from trezorlib import protobuf


class SimpleEnum(IntEnum):
    FOO = 0
    BAR = 5
    QUUX = 13


class SimpleMessage(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("uvarint", "uint64"),
        2: protobuf.Field("svarint", "sint64"),
        3: protobuf.Field("bool", "bool"),
        4: protobuf.Field("bytes", "bytes"),
        5: protobuf.Field("unicode", "string"),
        6: protobuf.Field("enum", SimpleEnum),
        7: protobuf.Field("rep_int", "uint64", repeated=True),
        8: protobuf.Field("rep_str", "string", repeated=True),
        9: protobuf.Field("rep_enum", SimpleEnum, repeated=True),
    }


class NestedMessage(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("scalar", "uint64"),
        2: protobuf.Field("nested", SimpleMessage),
        3: protobuf.Field("repeated", SimpleMessage, repeated=True),
    }


class RequiredFields(protobuf.MessageType):
    FIELDS = {
        1: protobuf.Field("scalar", "uint64", required=True),
    }


def test_get_field():
    # smoke test
    field = SimpleMessage.get_field("bool")
    assert field.name == "bool"
    assert field.type == "bool"
    assert field.repeated is False
    assert field.required is False
    assert field.default is None


def test_dict_roundtrip():
    msg = SimpleMessage(
        uvarint=5,
        svarint=-13,
        bool=False,
        bytes=b"\xca\xfe\x00\xfe",
        unicode="žluťoučký kůň",
        enum=SimpleEnum.BAR,
        rep_int=[1, 2, 3],
        rep_str=["a", "b", "c"],
        rep_enum=[SimpleEnum.FOO, SimpleEnum.BAR, SimpleEnum.QUUX],
    )

    converted = protobuf.to_dict(msg)
    recovered = protobuf.dict_to_proto(SimpleMessage, converted)

    assert recovered == msg


def test_to_dict():
    msg = SimpleMessage(
        uvarint=5,
        svarint=-13,
        bool=False,
        bytes=b"\xca\xfe\x00\xfe",
        unicode="žluťoučký kůň",
        enum=SimpleEnum.BAR,
        rep_int=[1, 2, 3],
        rep_str=["a", "b", "c"],
        rep_enum=[SimpleEnum.FOO, SimpleEnum.BAR, SimpleEnum.QUUX],
    )

    converted = protobuf.to_dict(msg)

    fields = [field.name for field in msg.FIELDS.values()]
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

    for field in SimpleMessage.FIELDS.values():
        if field.name not in dictdata:
            if field.repeated:
                assert getattr(recovered, field.name) == []
            else:
                assert getattr(recovered, field.name) is None


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


def test_nested_recover():
    dictdata = {"nested": {}}
    recovered = protobuf.dict_to_proto(NestedMessage, dictdata)
    assert isinstance(recovered.nested, SimpleMessage)


@pytest.mark.xfail(reason="formatting broken because of size counting")
def test_unknown_enum_to_str():
    simple = SimpleMessage(enum=SimpleEnum.QUUX)
    string = protobuf.format_message(simple)
    assert "enum: QUUX (13)" in string

    simple = SimpleMessage(enum=6000)
    string = protobuf.format_message(simple)
    assert "enum: 6000" in string


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
