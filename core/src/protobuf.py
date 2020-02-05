"""
Extremely minimal streaming codec for a subset of protobuf.  Supports uint32,
bytes, string, embedded message and repeated fields.
"""

from micropython import const

if False:
    from typing import Any, Dict, Iterable, List, Optional, Type, TypeVar, Union
    from typing_extensions import Protocol

    class AsyncReader(Protocol):
        async def areadinto(self, buf: bytearray) -> int:
            """
            Reads `len(buf)` bytes into `buf`, or raises `EOFError`.
            """

    class AsyncWriter(Protocol):
        async def awrite(self, buf: bytes) -> int:
            """
            Writes all bytes from `buf`, or raises `EOFError`.
            """


_UVARINT_BUFFER = bytearray(1)


async def load_uvarint(reader: AsyncReader) -> int:
    buffer = _UVARINT_BUFFER
    result = 0
    shift = 0
    byte = 0x80
    while byte & 0x80:
        await reader.areadinto(buffer)
        byte = buffer[0]
        result += (byte & 0x7F) << shift
        shift += 7
    return result


async def dump_uvarint(writer: AsyncWriter, n: int) -> None:
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    buffer = _UVARINT_BUFFER
    shifted = 1
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        await writer.awrite(buffer)
        n = shifted


def count_uvarint(n: int) -> int:
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    if n <= 0x7F:
        return 1
    if n <= 0x3FFF:
        return 2
    if n <= 0x1FFFFF:
        return 3
    if n <= 0xFFFFFFF:
        return 4
    if n <= 0x7FFFFFFFF:
        return 5
    if n <= 0x3FFFFFFFFFF:
        return 6
    if n <= 0x1FFFFFFFFFFFF:
        return 7
    if n <= 0xFFFFFFFFFFFFFF:
        return 8
    if n <= 0x7FFFFFFFFFFFFFFF:
        return 9
    raise ValueError


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

    def __init__(self, name: str, enum_values: Iterable[int]) -> None:
        self.enum_values = enum_values

    def validate(self, fvalue: int) -> int:
        if fvalue in self.enum_values:
            return fvalue
        else:
            print("INVALID", fvalue, "IN", self.enum_values)
            raise TypeError("Invalid enum value")


class BytesType:
    WIRE_TYPE = 2


class UnicodeType:
    WIRE_TYPE = 2


class MessageType:
    WIRE_TYPE = 2

    # Type id for the wire codec.
    # Technically, not every protobuf message has this.
    MESSAGE_WIRE_TYPE = -1

    @classmethod
    def get_fields(cls) -> Dict:
        return {}

    def __init__(self, **kwargs: Any) -> None:
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])

    def __eq__(self, rhs: Any) -> bool:
        return self.__class__ is rhs.__class__ and self.__dict__ == rhs.__dict__

    def __repr__(self) -> str:
        return "<%s>" % self.__class__.__name__


class LimitedReader:
    def __init__(self, reader: AsyncReader, limit: int) -> None:
        self.reader = reader
        self.limit = limit

    async def areadinto(self, buf: bytearray) -> int:
        if self.limit < len(buf):
            raise EOFError
        else:
            nread = await self.reader.areadinto(buf)
            self.limit -= nread
            return nread


FLAG_REPEATED = const(1)

if False:
    LoadedMessageType = TypeVar("LoadedMessageType", bound=MessageType)


async def load_message(
    reader: AsyncReader, msg_type: Type[LoadedMessageType]
) -> LoadedMessageType:
    fields = msg_type.get_fields()
    msg = msg_type()

    if False:
        SingularValue = Union[int, bool, bytearray, str, MessageType]
        Value = Union[SingularValue, List[SingularValue]]
        fvalue = 0  # type: Value

    while True:
        try:
            fkey = await load_uvarint(reader)
        except EOFError:
            break  # no more fields to load

        ftag = fkey >> 3
        wtype = fkey & 7

        field = fields.get(ftag, None)

        if field is None:  # unknown field, skip it
            if wtype == 0:
                await load_uvarint(reader)
            elif wtype == 2:
                ivalue = await load_uvarint(reader)
                await reader.areadinto(bytearray(ivalue))
            else:
                raise ValueError
            continue

        fname, ftype, fflags = field
        if wtype != ftype.WIRE_TYPE:
            raise TypeError  # parsed wire type differs from the schema

        ivalue = await load_uvarint(reader)

        if ftype is UVarintType:
            fvalue = ivalue
        elif ftype is SVarintType:
            fvalue = uint_to_sint(ivalue)
        elif ftype is BoolType:
            fvalue = bool(ivalue)
        elif isinstance(ftype, EnumType):
            fvalue = ftype.validate(ivalue)
        elif ftype is BytesType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
        elif ftype is UnicodeType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
            fvalue = bytes(fvalue).decode()
        elif issubclass(ftype, MessageType):
            fvalue = await load_message(LimitedReader(reader, ivalue), ftype)
        else:
            raise TypeError  # field type is unknown

        if fflags & FLAG_REPEATED:
            pvalue = getattr(msg, fname, [])
            pvalue.append(fvalue)
            fvalue = pvalue
        setattr(msg, fname, fvalue)

    # fill missing fields
    for tag in fields:
        field = fields[tag]
        if not hasattr(msg, field[0]):
            setattr(msg, field[0], None)

    return msg


async def dump_message(
    writer: AsyncWriter, msg: MessageType, fields: Dict = None
) -> None:
    repvalue = [0]

    if fields is None:
        fields = msg.get_fields()

    for ftag in fields:
        fname, ftype, fflags = fields[ftag]

        fvalue = getattr(msg, fname, None)
        if fvalue is None:
            continue

        fkey = (ftag << 3) | ftype.WIRE_TYPE

        if not fflags & FLAG_REPEATED:
            repvalue[0] = fvalue
            fvalue = repvalue

        ffields = None  # type: Optional[Dict]

        for svalue in fvalue:
            await dump_uvarint(writer, fkey)

            if ftype is UVarintType:
                await dump_uvarint(writer, svalue)

            elif ftype is SVarintType:
                await dump_uvarint(writer, sint_to_uint(svalue))

            elif ftype is BoolType:
                await dump_uvarint(writer, int(svalue))

            elif isinstance(ftype, EnumType):
                await dump_uvarint(writer, svalue)

            elif ftype is BytesType:
                if isinstance(svalue, list):
                    await dump_uvarint(writer, _count_bytes_list(svalue))
                    for sub_svalue in svalue:
                        await writer.awrite(sub_svalue)
                else:
                    await dump_uvarint(writer, len(svalue))
                    await writer.awrite(svalue)

            elif ftype is UnicodeType:
                svalue = svalue.encode()
                await dump_uvarint(writer, len(svalue))
                await writer.awrite(svalue)

            elif issubclass(ftype, MessageType):
                if ffields is None:
                    ffields = ftype.get_fields()
                await dump_uvarint(writer, count_message(svalue, ffields))
                await dump_message(writer, svalue, ffields)

            else:
                raise TypeError


def count_message(msg: MessageType, fields: Dict = None) -> int:
    nbytes = 0
    repvalue = [0]

    if fields is None:
        fields = msg.get_fields()

    for ftag in fields:
        fname, ftype, fflags = fields[ftag]

        fvalue = getattr(msg, fname, None)
        if fvalue is None:
            continue

        fkey = (ftag << 3) | ftype.WIRE_TYPE

        if not fflags & FLAG_REPEATED:
            repvalue[0] = fvalue
            fvalue = repvalue

        # length of all the field keys
        nbytes += count_uvarint(fkey) * len(fvalue)

        if ftype is UVarintType:
            for svalue in fvalue:
                nbytes += count_uvarint(svalue)

        elif ftype is SVarintType:
            for svalue in fvalue:
                nbytes += count_uvarint(sint_to_uint(svalue))

        elif ftype is BoolType:
            for svalue in fvalue:
                nbytes += count_uvarint(int(svalue))

        elif isinstance(ftype, EnumType):
            for svalue in fvalue:
                nbytes += count_uvarint(svalue)

        elif ftype is BytesType:
            for svalue in fvalue:
                if isinstance(svalue, list):
                    svalue = _count_bytes_list(svalue)
                else:
                    svalue = len(svalue)
                nbytes += count_uvarint(svalue)
                nbytes += svalue

        elif ftype is UnicodeType:
            for svalue in fvalue:
                svalue = len(svalue.encode())
                nbytes += count_uvarint(svalue)
                nbytes += svalue

        elif issubclass(ftype, MessageType):
            ffields = ftype.get_fields()
            for svalue in fvalue:
                fsize = count_message(svalue, ffields)
                nbytes += count_uvarint(fsize)
                nbytes += fsize
            del ffields

        else:
            raise TypeError

    return nbytes


def _count_bytes_list(svalue: List[bytes]) -> int:
    res = 0
    for x in svalue:
        res += len(x)
    return res
