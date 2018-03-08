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
    buffer = _UVARINT_BUFFER
    shifted = True
    while shifted:
        shifted = n >> 7
        buffer[0] = (n & 0x7F) | (0x80 if shifted else 0x00)
        await writer.awrite(buffer)
        n = shifted


class UVarintType:
    WIRE_TYPE = 0


class Sint32Type:
    WIRE_TYPE = 0


class Sint64Type:
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
        return (self.__class__ is rhs.__class__ and
                self.__dict__ == rhs.__dict__)

    def __repr__(self):
        return '<%s>' % self.__class__.__name__


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
        elif ftype is Sint32Type:
            fvalue = (ivalue >> 1) ^ ((ivalue << 31) & 0xffffffff)
        elif ftype is Sint64Type:
            fvalue = (ivalue >> 1) ^ ((ivalue << 63) & 0xffffffffffffffff)
        elif ftype is BoolType:
            fvalue = bool(ivalue)
        elif ftype is BytesType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
        elif ftype is UnicodeType:
            fvalue = bytearray(ivalue)
            await reader.areadinto(fvalue)
            fvalue = str(fvalue, 'utf8')
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
        field = fields[ftag]
        fname = field[0]
        ftype = field[1]
        fflags = field[2]

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

            elif ftype is Sint32Type:
                await dump_uvarint(writer, ((svalue << 1) & 0xffffffff) ^ (svalue >> 31))

            elif ftype is Sint64Type:
                await dump_uvarint(writer, ((svalue << 1) & 0xffffffffffffffff) ^ (svalue >> 63))

            elif ftype is BoolType:
                await dump_uvarint(writer, int(svalue))

            elif ftype is BytesType:
                await dump_uvarint(writer, len(svalue))
                await writer.awrite(svalue)

            elif ftype is UnicodeType:
                bvalue = bytes(svalue, 'utf8')
                await dump_uvarint(writer, len(bvalue))
                await writer.awrite(bvalue)

            elif issubclass(ftype, MessageType):
                counter = CountingWriter()
                await dump_message(counter, svalue)
                await dump_uvarint(writer, counter.size)
                await dump_message(writer, svalue)

            else:
                raise TypeError
