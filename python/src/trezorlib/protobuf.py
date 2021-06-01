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

"""
Extremely minimal streaming codec for a subset of protobuf.
Supports uint32, bytes, string, embedded message and repeated fields.

For de-serializing (loading) protobuf types, object with `Reader` interface is required.
For serializing (dumping) protobuf types, object with `Writer` interface is required.
"""

import logging
import warnings
from enum import IntEnum
from io import BytesIO
from itertools import zip_longest
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

import attr
from typing_extensions import Protocol

MT = TypeVar("MT", bound="MessageType")


class Reader(Protocol):
    def readinto(self, buffer: bytearray) -> int:
        """
        Reads exactly `len(buffer)` bytes into `buffer`. Returns number of bytes read,
        or 0 if it cannot read that much.
        """


class Writer(Protocol):
    def write(self, buffer: bytes) -> int:
        """
        Writes all bytes from `buffer`, or raises `EOFError`
        """


_UVARINT_BUFFER = bytearray(1)

LOG = logging.getLogger(__name__)


def safe_issubclass(value, cls):
    return isinstance(value, type) and issubclass(value, cls)


def load_uvarint(reader: Reader) -> int:
    buffer = _UVARINT_BUFFER
    result = 0
    shift = 0
    byte = 0x80
    bytes_read = 0
    while byte & 0x80:
        if reader.readinto(buffer) == 0:
            if bytes_read > 0:
                raise IOError("Interrupted UVarint")
            else:
                raise EOFError
        bytes_read += 1
        byte = buffer[0]
        result += (byte & 0x7F) << shift
        shift += 7
    return result


def dump_uvarint(writer: Writer, n: int) -> None:
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    buffer = _UVARINT_BUFFER
    shifted = 1
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        writer.write(buffer)
        n = shifted


# protobuf interleaved signed encoding:
# https://developers.google.com/protocol-buffers/docs/encoding#structure
# the idea is to save the sign in LSbit instead of twos-complement.
# so counting up, you go: 0, -1, 1, -2, 2, ... (as the first bit changes, sign flips)
#
# To achieve this with a twos-complement number:
# 1. shift left by 1, leaving LSbit free
# 2. if the number is negative, do bitwise negation.
#    This keeps positive number the same, and converts negative from twos-complement
#    to the appropriate value, while setting the sign bit.
#
# The original algorithm makes use of the fact that arithmetic (signed) shift
# keeps the sign bits, so for a n-bit number, (x >> n) gets us "all sign bits".
# Then you can take "number XOR all-sign-bits", which is XOR 0 (identity) for positive
# and XOR 1 (bitwise negation) for negative. Cute and efficient.
#
# But this is harder in Python because we don't natively know the bit size of the number.
# So we have to branch on whether the number is negative.


def sint_to_uint(sint: int) -> int:
    res = sint << 1
    if sint < 0:
        res = ~res
    return res


def uint_to_sint(uint: int) -> int:
    sign = uint & 1
    res = uint >> 1
    if sign:
        res = ~res
    return res


WIRE_TYPE_INT = 0
WIRE_TYPE_LENGTH = 2

WIRE_TYPES = {
    "uint32": WIRE_TYPE_INT,
    "uint64": WIRE_TYPE_INT,
    "sint32": WIRE_TYPE_INT,
    "sint64": WIRE_TYPE_INT,
    "bool": WIRE_TYPE_INT,
    "bytes": WIRE_TYPE_LENGTH,
    "string": WIRE_TYPE_LENGTH,
}

REQUIRED_FIELD_PLACEHOLDER = object()


@attr.s(auto_attribs=True)
class Field:
    name: str
    type: Union[str, "MessageType", IntEnum]
    repeated: bool = attr.ib(default=False)
    required: bool = attr.ib(default=False)
    default: object = attr.ib(default=None)

    @property
    def wire_type(self) -> int:
        if self.type in WIRE_TYPES:
            return WIRE_TYPES[self.type]

        if safe_issubclass(self.type, MessageType):
            return WIRE_TYPE_LENGTH

        if safe_issubclass(self.type, IntEnum):
            return WIRE_TYPE_INT

        raise ValueError(f"Unrecognized type for field {self.name}")

    def value_fits(self, value: int) -> bool:
        if self.type == "uint32":
            return 0 <= value < 2 ** 32
        if self.type == "uint64":
            return 0 <= value < 2 ** 64
        if self.type == "sint32":
            return -(2 ** 31) <= value < 2 ** 31
        if self.type == "sint64":
            return -(2 ** 63) <= value < 2 ** 63

        raise ValueError(f"Cannot check range bounds for {self.type}")


class _MessageTypeMeta(type):
    def __init__(cls, name, bases, d) -> None:
        super().__init__(name, bases, d)
        if name != "MessageType":
            cls.__init__ = MessageType.__init__


class MessageType(metaclass=_MessageTypeMeta):
    MESSAGE_WIRE_TYPE: Optional[int] = None
    UNSTABLE: bool = False

    FIELDS: Dict[int, Field] = {}

    @classmethod
    def get_field(cls, name: str) -> Optional[Field]:
        return next((f for f in cls.FIELDS.values() if f.name == name), None)

    def __init__(self, *args, **kwargs: Any) -> None:
        if args:
            warnings.warn(
                "Positional arguments for MessageType are deprecated",
                DeprecationWarning,
                stacklevel=2,
            )
        # process fields one by one
        MISSING = object()
        for field, val in zip_longest(self.FIELDS.values(), args, fillvalue=MISSING):
            if field is MISSING:
                raise TypeError("too many positional arguments")
            if field.name in kwargs and val is not MISSING:
                # both *args and **kwargs specify the same thing
                raise TypeError(f"got multiple values for argument '{field.name}'")
            elif field.name in kwargs:
                # set in kwargs but not in args
                setattr(self, field.name, kwargs[field.name])
            elif val is not MISSING:
                # set in args but not in kwargs
                setattr(self, field.name, val)
            else:
                # not set at all, pick a default
                if field.repeated:
                    default = []
                elif field.required:
                    warnings.warn(
                        f"Value of required field '{field.name}' must be provided in constructor",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    default = REQUIRED_FIELD_PLACEHOLDER
                else:
                    default = field.default
                setattr(self, field.name, default)

    def __eq__(self, rhs: Any) -> bool:
        return self.__class__ is rhs.__class__ and self.__dict__ == rhs.__dict__

    def __repr__(self) -> str:
        d = {}
        for key, value in self.__dict__.items():
            if value is None or value == []:
                continue
            d[key] = value
        return "<%s: %s>" % (self.__class__.__name__, d)

    def ByteSize(self) -> int:
        data = BytesIO()
        dump_message(data, self)
        return len(data.getvalue())


class LimitedReader:
    def __init__(self, reader: Reader, limit: int) -> None:
        self.reader = reader
        self.limit = limit

    def readinto(self, buf: bytearray) -> int:
        if self.limit < len(buf):
            return 0
        else:
            nread = self.reader.readinto(buf)
            self.limit -= nread
            return nread


class CountingWriter:
    def __init__(self) -> None:
        self.size = 0

    def write(self, buf: bytes) -> int:
        nwritten = len(buf)
        self.size += nwritten
        return nwritten


def decode_packed_array_field(field: Field, reader: Reader) -> List[Any]:
    assert field.repeated, "Not decoding packed array into non-repeated field"
    length = load_uvarint(reader)
    packed_reader = LimitedReader(reader, length)
    values = []
    try:
        while True:
            values.append(decode_varint_field(field, packed_reader))
    except EOFError:
        pass
    return values


def decode_varint_field(field: Field, reader: Reader) -> Union[int, bool, IntEnum]:
    assert field.wire_type == WIRE_TYPE_INT, f"Field {field.name} is not varint-encoded"
    value = load_uvarint(reader)
    if safe_issubclass(field.type, IntEnum):
        try:
            return field.type(value)
        except ValueError as e:
            # treat enum errors as warnings
            LOG.info(f"On field {field.name}: {e}")
            return value

    if field.type.startswith("uint"):
        if not field.value_fits(value):
            LOG.info(
                f"On field {field.name}: value {value} out of range for {field.type}"
            )
        return value

    if field.type.startswith("sint"):
        value = uint_to_sint(value)
        if not field.value_fits(value):
            LOG.info(
                f"On field {field.name}: value {value} out of range for {field.type}"
            )
        return value

    if field.type == "bool":
        return bool(value)

    raise TypeError  # not a varint field or unknown type


def decode_length_delimited_field(
    field: Field, reader: Reader
) -> Union[bytes, str, MessageType]:
    value = load_uvarint(reader)
    if field.type == "bytes":
        buf = bytearray(value)
        reader.readinto(buf)
        return bytes(buf)

    if field.type == "string":
        buf = bytearray(value)
        reader.readinto(buf)
        return buf.decode()

    if safe_issubclass(field.type, MessageType):
        return load_message(LimitedReader(reader, value), field.type)

    raise TypeError  # field type is unknown


def load_message(reader: Reader, msg_type: Type[MT]) -> MT:
    msg_dict = {}
    # pre-seed the dict
    for field in msg_type.FIELDS.values():
        if field.repeated:
            msg_dict[field.name] = []
        elif not field.required:
            msg_dict[field.name] = field.default

    while True:
        try:
            fkey = load_uvarint(reader)
        except EOFError:
            break  # no more fields to load

        ftag = fkey >> 3
        wtype = fkey & 7

        field = msg_type.FIELDS.get(ftag, None)

        if field is None:  # unknown field, skip it
            if wtype == WIRE_TYPE_INT:
                load_uvarint(reader)
            elif wtype == WIRE_TYPE_LENGTH:
                ivalue = load_uvarint(reader)
                reader.readinto(bytearray(ivalue))
            else:
                raise ValueError
            continue

        if (
            wtype == WIRE_TYPE_LENGTH
            and field.wire_type == WIRE_TYPE_INT
            and field.repeated
        ):
            # packed array
            fvalues = decode_packed_array_field(field, reader)

        elif wtype != field.wire_type:
            raise ValueError(f"Field {field.name} received value does not match schema")

        elif wtype == WIRE_TYPE_LENGTH:
            fvalues = [decode_length_delimited_field(field, reader)]

        elif wtype == WIRE_TYPE_INT:
            fvalues = [decode_varint_field(field, reader)]

        else:
            raise TypeError  # unknown wire type

        if field.repeated:
            msg_dict[field.name].extend(fvalues)
        elif len(fvalues) != 1:
            raise ValueError("Unexpected multiple values in non-repeating field")
        else:
            msg_dict[field.name] = fvalues[0]

    for field in msg_type.FIELDS.values():
        if field.required and field.name not in msg_dict:
            raise ValueError(f"Did not receive value for field {field.name}")
    return msg_type(**msg_dict)


def dump_message(writer: Writer, msg: MessageType) -> None:
    repvalue = [0]
    mtype = msg.__class__

    for ftag, field in mtype.FIELDS.items():
        fvalue = getattr(msg, field.name, None)

        if fvalue is REQUIRED_FIELD_PLACEHOLDER:
            raise ValueError(f"Required value of field {field.name} was not provided")

        if fvalue is None:
            # not sending empty values
            continue

        fkey = (ftag << 3) | field.wire_type

        if not field.repeated:
            repvalue[0] = fvalue
            fvalue = repvalue

        for svalue in fvalue:
            dump_uvarint(writer, fkey)

            if safe_issubclass(field.type, MessageType):
                counter = CountingWriter()
                dump_message(counter, svalue)
                dump_uvarint(writer, counter.size)
                dump_message(writer, svalue)

            elif safe_issubclass(field.type, IntEnum):
                if svalue not in field.type.__members__.values():
                    raise ValueError(
                        f"Value {svalue} in field {field.name} unknown for {field.type.__name__}"
                    )
                dump_uvarint(writer, svalue)

            elif field.type.startswith("uint"):
                if not field.value_fits(svalue):
                    raise ValueError(
                        f"Value {svalue} in field {field.name} does not fit into {field.type}"
                    )
                dump_uvarint(writer, svalue)

            elif field.type.startswith("sint"):
                if not field.value_fits(svalue):
                    raise ValueError(
                        f"Value {svalue} in field {field.name} does not fit into {field.type}"
                    )
                dump_uvarint(writer, sint_to_uint(svalue))

            elif field.type == "bool":
                dump_uvarint(writer, int(svalue))

            elif field.type == "bytes":
                dump_uvarint(writer, len(svalue))
                writer.write(svalue)

            elif field.type == "string":
                svalue_bytes = svalue.encode()
                dump_uvarint(writer, len(svalue_bytes))
                writer.write(svalue_bytes)

            else:
                raise TypeError


def format_message(
    pb: MessageType,
    indent: int = 0,
    sep: str = " " * 4,
    truncate_after: Optional[int] = 256,
    truncate_to: Optional[int] = 64,
) -> str:
    def mostly_printable(bytes: bytes) -> bool:
        if not bytes:
            return True
        printable = sum(1 for byte in bytes if 0x20 <= byte <= 0x7E)
        return printable / len(bytes) > 0.8

    def pformat(name: str, value: Any, indent: int) -> str:
        level = sep * indent
        leadin = sep * (indent + 1)
        field = pb.get_field(name)

        if isinstance(value, MessageType):
            return format_message(value, indent, sep)

        if isinstance(value, list):
            # short list of simple values
            if not value or all(isinstance(x, int) for x in value):
                return repr(value)

            # long list, one line per entry
            lines = ["[", level + "]"]
            lines[1:1] = [leadin + pformat(name, x, indent + 1) + "," for x in value]
            return "\n".join(lines)

        if isinstance(value, dict):
            lines = ["{"]
            for key, val in sorted(value.items()):
                if val is None or val == []:
                    continue
                lines.append(leadin + key + ": " + pformat(key, val, indent + 1) + ",")
            lines.append(level + "}")
            return "\n".join(lines)

        if isinstance(value, (bytes, bytearray)):
            length = len(value)
            suffix = ""
            if truncate_after and length > truncate_after:
                suffix = "..."
                value = value[: truncate_to or 0]
            if mostly_printable(value):
                output = repr(value)
            else:
                output = "0x" + value.hex()
            return "{} bytes {}{}".format(length, output, suffix)

        if isinstance(value, int) and safe_issubclass(field.type, IntEnum):
            try:
                return "{} ({})".format(field.type(value).name, value)
            except ValueError:
                return str(value)

        return repr(value)

    return "{name} ({size} bytes) {content}".format(
        name=pb.__class__.__name__,
        size=pb.ByteSize(),
        content=pformat("", pb.__dict__, indent),
    )


def value_to_proto(field: Field, value: Any) -> Any:
    if safe_issubclass(field.type, MessageType):
        raise TypeError("value_to_proto only converts simple values")

    if safe_issubclass(field.type, IntEnum):
        if isinstance(value, str):
            return field.type.__members__[value]
        else:
            try:
                return field.type(value)
            except ValueError as e:
                LOG.info(f"On field {field.name}: {e}")
                return int(value)

    if "int" in field.type:
        return int(value)

    if field.type == "bool":
        return bool(value)

    if field.type == "string":
        return str(value)

    if field.type == "bytes":
        if isinstance(value, str):
            return bytes.fromhex(value)
        elif isinstance(value, bytes):
            return value
        else:
            raise TypeError(f"can't convert {type(value)} value to bytes")


def dict_to_proto(message_type: Type[MT], d: Dict[str, Any]) -> MT:
    params = {}
    for field in message_type.FIELDS.values():
        value = d.get(field.name)
        if value is None:
            continue

        if not field.repeated:
            value = [value]

        if safe_issubclass(field.type, MessageType):
            newvalue = [dict_to_proto(field.type, v) for v in value]
        else:
            newvalue = [value_to_proto(field, v) for v in value]

        if not field.repeated:
            newvalue = newvalue[0]

        params[field.name] = newvalue
    return message_type(**params)


def to_dict(msg: MessageType, hexlify_bytes: bool = True) -> Dict[str, Any]:
    def convert_value(field: Field, value: Any) -> Any:
        if hexlify_bytes and isinstance(value, bytes):
            return value.hex()
        elif isinstance(value, MessageType):
            return to_dict(value, hexlify_bytes)
        elif isinstance(value, list):
            return [convert_value(field, v) for v in value]
        elif isinstance(value, IntEnum):
            return value.name
        else:
            return value

    res = {}
    for key, value in msg.__dict__.items():
        if value is None or value == []:
            continue
        res[key] = convert_value(msg.get_field(key), value)

    return res
