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
from io import BytesIO
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import Protocol

FieldType = Union[
    "EnumType",
    Type["MessageType"],
    Type["UVarintType"],
    Type["SVarintType"],
    Type["BoolType"],
    Type["UnicodeType"],
    Type["BytesType"],
]
FieldInfo = Tuple[str, FieldType, int]
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


class UVarintType:
    WIRE_TYPE = 0


class SVarintType:
    WIRE_TYPE = 0


class BoolType:
    WIRE_TYPE = 0


class EnumType:
    WIRE_TYPE = 0

    def __init__(self, enum_name: str, enum_values: Iterable[int]) -> None:
        self.enum_name = enum_name
        self.enum_values = enum_values

    def validate(self, fvalue: int) -> int:
        if fvalue not in self.enum_values:
            # raise TypeError("Invalid enum value")
            LOG.info("Value {} unknown for type {}".format(fvalue, self.enum_name))
        return fvalue

    def to_str(self, fvalue: int) -> str:
        from . import messages

        module = getattr(messages, self.enum_name)
        for name in dir(module):
            if name.startswith("__"):
                continue
            if getattr(module, name) == fvalue:
                return name
        else:
            raise TypeError("Invalid enum value")

    def from_str(self, fstr: str) -> int:
        try:
            from . import messages

            module = getattr(messages, self.enum_name)
            ivalue = getattr(module, fstr)
            if isinstance(ivalue, int):
                return ivalue
            else:
                raise TypeError("Invalid enum value")
        except AttributeError:
            raise TypeError("Invalid enum value") from None


class BytesType:
    WIRE_TYPE = 2


class UnicodeType:
    WIRE_TYPE = 2


class MessageType:
    WIRE_TYPE = 2

    @classmethod
    def get_fields(cls) -> Dict[int, FieldInfo]:
        return {}

    @classmethod
    def get_field_type(cls, name: str) -> Optional[FieldType]:
        for fname, ftype, flags in cls.get_fields().values():
            if fname == name:
                return ftype
        return None

    def __init__(self, **kwargs: Any) -> None:
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])
        self._fill_missing()

    def __eq__(self, rhs: Any) -> bool:
        return self.__class__ is rhs.__class__ and self.__dict__ == rhs.__dict__

    def __repr__(self) -> str:
        d = {}
        for key, value in self.__dict__.items():
            if value is None or value == []:
                continue
            d[key] = value
        return "<%s: %s>" % (self.__class__.__name__, d)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def keys(self) -> Iterator[str]:
        return (name for name, _, _ in self.get_fields().values())

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def _fill_missing(self) -> None:
        # fill missing fields
        for fname, ftype, fflags in self.get_fields().values():
            if not hasattr(self, fname):
                if fflags & FLAG_REPEATED:
                    setattr(self, fname, [])
                else:
                    setattr(self, fname, None)

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


FLAG_REPEATED = 1


def decode_packed_array_field(ftype: FieldType, reader: Reader) -> List[Any]:
    length = load_uvarint(reader)
    packed_reader = LimitedReader(reader, length)
    values = []
    try:
        while True:
            values.append(decode_varint_field(ftype, packed_reader))
    except EOFError:
        pass
    return values


def decode_varint_field(ftype: FieldType, reader: Reader) -> Union[int, bool]:
    value = load_uvarint(reader)
    if ftype is UVarintType:
        return value
    elif ftype is SVarintType:
        return uint_to_sint(value)
    elif ftype is BoolType:
        return bool(value)
    elif isinstance(ftype, EnumType):
        return ftype.validate(value)
    else:
        raise TypeError  # not a varint field or unknown type


def decode_length_delimited_field(
    ftype: FieldType, reader: Reader
) -> Union[bytes, str, MessageType]:
    value = load_uvarint(reader)
    if ftype is BytesType:
        buf = bytearray(value)
        reader.readinto(buf)
        return bytes(buf)
    elif ftype is UnicodeType:
        buf = bytearray(value)
        reader.readinto(buf)
        return buf.decode()
    elif isinstance(ftype, type) and issubclass(ftype, MessageType):
        return load_message(LimitedReader(reader, value), ftype)
    else:
        raise TypeError  # field type is unknown


def load_message(reader: Reader, msg_type: Type[MT]) -> MT:
    fields = msg_type.get_fields()
    msg = msg_type()

    while True:
        try:
            fkey = load_uvarint(reader)
        except EOFError:
            break  # no more fields to load

        ftag = fkey >> 3
        wtype = fkey & 7

        field = fields.get(ftag, None)

        if field is None:  # unknown field, skip it
            if wtype == 0:
                load_uvarint(reader)
            elif wtype == 2:
                ivalue = load_uvarint(reader)
                reader.readinto(bytearray(ivalue))
            else:
                raise ValueError
            continue

        fname, ftype, fflags = field

        if wtype == 2 and ftype.WIRE_TYPE == 0 and fflags & FLAG_REPEATED:
            # packed array
            fvalues = decode_packed_array_field(ftype, reader)

        elif wtype != ftype.WIRE_TYPE:
            raise TypeError  # parsed wire type differs from the schema

        elif wtype == 2:
            fvalues = [decode_length_delimited_field(ftype, reader)]

        elif wtype == 0:
            fvalues = [decode_varint_field(ftype, reader)]

        else:
            raise TypeError  # unknown wire type

        if fflags & FLAG_REPEATED:
            pvalue = getattr(msg, fname)
            pvalue.extend(fvalues)
            fvalue = pvalue
        elif len(fvalues) != 1:
            raise ValueError("Unexpected multiple values in non-repeating field")
        else:
            fvalue = fvalues[0]

        setattr(msg, fname, fvalue)

    return msg


def dump_message(writer: Writer, msg: MessageType) -> None:
    repvalue = [0]
    mtype = msg.__class__
    fields = mtype.get_fields()

    for ftag in fields:
        fname, ftype, fflags = fields[ftag]

        fvalue = getattr(msg, fname, None)
        if fvalue is None:
            continue

        fkey = (ftag << 3) | ftype.WIRE_TYPE

        if not fflags & FLAG_REPEATED:
            repvalue[0] = fvalue
            fvalue = repvalue

        for svalue in fvalue:
            dump_uvarint(writer, fkey)

            if ftype is UVarintType:
                dump_uvarint(writer, svalue)

            elif ftype is SVarintType:
                dump_uvarint(writer, sint_to_uint(svalue))

            elif ftype is BoolType:
                dump_uvarint(writer, int(svalue))

            elif isinstance(ftype, EnumType):
                dump_uvarint(writer, ftype.validate(svalue))

            elif ftype is BytesType:
                dump_uvarint(writer, len(svalue))
                writer.write(svalue)

            elif ftype is UnicodeType:
                svalue_bytes = svalue.encode()
                dump_uvarint(writer, len(svalue_bytes))
                writer.write(svalue_bytes)

            elif issubclass(ftype, MessageType):
                counter = CountingWriter()
                dump_message(counter, svalue)
                dump_uvarint(writer, counter.size)
                dump_message(writer, svalue)

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
        ftype = pb.get_field_type(name)

        if isinstance(value, MessageType):
            return format_message(value, indent, sep)

        if isinstance(value, list):
            # short list of simple values
            if not value or isinstance(value, (UVarintType, SVarintType, BoolType)):
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

        if isinstance(value, int) and isinstance(ftype, EnumType):
            try:
                return "{} ({})".format(ftype.to_str(value), value)
            except TypeError:
                return str(value)

        return repr(value)

    return "{name} ({size} bytes) {content}".format(
        name=pb.__class__.__name__,
        size=pb.ByteSize(),
        content=pformat("", pb.__dict__, indent),
    )


def value_to_proto(ftype: FieldType, value: Any) -> Any:
    if isinstance(ftype, type) and issubclass(ftype, MessageType):
        raise TypeError("value_to_proto only converts simple values")

    if isinstance(ftype, EnumType):
        if isinstance(value, str):
            return ftype.from_str(value)
        else:
            return int(value)

    if ftype in (UVarintType, SVarintType):
        return int(value)

    if ftype is BoolType:
        return bool(value)

    if ftype is UnicodeType:
        return str(value)

    if ftype is BytesType:
        if isinstance(value, str):
            return bytes.fromhex(value)
        elif isinstance(value, bytes):
            return value
        else:
            raise TypeError("can't convert {} value to bytes".format(type(value)))


def dict_to_proto(message_type: Type[MT], d: Dict[str, Any]) -> MT:
    params = {}
    for fname, ftype, fflags in message_type.get_fields().values():
        repeated = fflags & FLAG_REPEATED
        value = d.get(fname)
        if value is None:
            continue

        if not repeated:
            value = [value]

        if isinstance(ftype, type) and issubclass(ftype, MessageType):
            function = dict_to_proto  # type: Callable[[Any, Any], Any]
        else:
            function = value_to_proto

        newvalue = [function(ftype, v) for v in value]

        if not repeated:
            newvalue = newvalue[0]

        params[fname] = newvalue
    return message_type(**params)


def to_dict(msg: MessageType, hexlify_bytes: bool = True) -> Dict[str, Any]:
    def convert_value(ftype: FieldType, value: Any) -> Any:
        if hexlify_bytes and isinstance(value, bytes):
            return value.hex()
        elif isinstance(value, MessageType):
            return to_dict(value, hexlify_bytes)
        elif isinstance(value, list):
            return [convert_value(ftype, v) for v in value]
        elif isinstance(value, int) and isinstance(ftype, EnumType):
            try:
                return ftype.to_str(value)
            except TypeError:
                return value
        else:
            return value

    res = {}
    for key, value in msg.__dict__.items():
        if value is None or value == []:
            continue
        res[key] = convert_value(msg.get_field_type(key), value)

    return res
