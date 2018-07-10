'''
Extremely minimal streaming codec for a subset of protobuf.  Supports uint32,
bytes, string, embedded message and repeated fields.

For de-serializing (loading) protobuf types, object with `AsyncReader`
interface is required:

>>> class AsyncReader:
>>>     async def areadinto(self, buffer):
>>>         """
>>>         Reads `len(buffer)` bytes into `buffer`, or raises `EOFError`.
>>>         """

For serializing (dumping) protobuf types, object with `AsyncWriter` interface is
required:

>>> class AsyncWriter:
>>>     async def awrite(self, buffer):
>>>         """
>>>         Writes all bytes from `buffer`, or raises `EOFError`.
>>>         """
'''

from micropython import const

_UVARINT_BUFFER = bytearray(1)


async def load_uvarint(reader):
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


async def dump_uvarint(writer, n):
    if n < 0:
        raise ValueError("Cannot dump signed value, convert it to unsigned first.")
    buffer = _UVARINT_BUFFER
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        await writer.awrite(buffer)
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


def sint_to_uint(sint):
    res = sint << 1
    if sint < 0:
        res = ~res
    return res


def uint_to_sint(uint):
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


class BytesType:
    WIRE_TYPE = 2


class UnicodeType:
    WIRE_TYPE = 2


class MessageType:
    WIRE_TYPE = 2
    FIELDS = {}

    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])

    def __eq__(self, rhs):
        return self.__class__ is rhs.__class__ and self.__dict__ == rhs.__dict__

    def __repr__(self):
        return "<%s>" % self.__class__.__name__


class LimitedReader:
    def __init__(self, reader, limit):
        self.reader = reader
        self.limit = limit

    async def areadinto(self, buf):
        if self.limit < len(buf):
            raise EOFError
        else:
            nread = await self.reader.areadinto(buf)
            self.limit -= nread
            return nread


class CountingWriter:
    def __init__(self):
        self.size = 0

    async def awrite(self, buf):
        nwritten = len(buf)
        self.size += nwritten
        return nwritten


FLAG_REPEATED = const(1)


async def load_message(reader, msg_type):
    fields = msg_type.FIELDS
    msg = msg_type()

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
        elif ftype is BytesType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
        elif ftype is UnicodeType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
            fvalue = str(fvalue, "utf8")
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
    for tag in msg.FIELDS:
        field = msg.FIELDS[tag]
        if not hasattr(msg, field[0]):
            setattr(msg, field[0], None)

    return msg


async def dump_message(writer, msg):
    repvalue = [0]
    mtype = msg.__class__
    fields = mtype.FIELDS

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
            await dump_uvarint(writer, fkey)

            if ftype is UVarintType:
                await dump_uvarint(writer, svalue)

            elif ftype is SVarintType:
                await dump_uvarint(writer, sint_to_uint(svalue))

            elif ftype is BoolType:
                await dump_uvarint(writer, int(svalue))

            elif ftype is BytesType:
                await dump_uvarint(writer, len(svalue))
                await writer.awrite(svalue)

            elif ftype is UnicodeType:
                bvalue = bytes(svalue, "utf8")
                await dump_uvarint(writer, len(bvalue))
                await writer.awrite(bvalue)

            elif issubclass(ftype, MessageType):
                counter = CountingWriter()
                await dump_message(counter, svalue)
                await dump_uvarint(writer, counter.size)
                await dump_message(writer, svalue)

            else:
                raise TypeError
