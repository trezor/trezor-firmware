'''
Streaming protobuf codec.

Handles asynchronous encoding and decoding of protobuf value streams.

Value format: ((field_name, field_type, field_flags), field_value)
    field_name (str):  Field name string.
    field_type (Type): Subclass of Type.
    field_flags (int): Field bit flags: `FLAG_REPEATED`.
    field_value (Any): Depends on field_type.
                       MessageTypes have `field_value == None`.

Type classes are either scalar or message-like.  `load()` generators of
scalar types return the value, message types stream it to a target
generator as described above.  All types can be loaded and dumped
synchronously with `loads()` and `dumps()`.
'''

from micropython import const
from streams import StreamReader, BufferWriter


def build_protobuf_message(message_type, callback=None, *args):
    message = message_type()
    try:
        while True:
            field, fvalue = yield
            fname, ftype, fflags = field
            if issubclass(ftype, MessageType):
                fvalue = yield from build_protobuf_message(ftype)
            if fflags & FLAG_REPEATED:
                prev_value = getattr(message, fname, [])
                prev_value.append(fvalue)
                fvalue = prev_value
            setattr(message, fname, fvalue)
    except EOFError:
        if callback is not None:
            callback(message, *args)
        return message


class Type:

    @classmethod
    def loads(cls, value):
        source = StreamReader(value, len(value))
        loader = cls.load(source)
        try:
            while True:
                loader.send(None)
        except StopIteration as e:
            return e.value

    @classmethod
    def dumps(cls, value):
        target = BufferWriter()
        dumper = cls.dump(value, target)
        try:
            while True:
                dumper.send(None)
        except StopIteration:
            return target.buffer


_uvarint_buffer = bytearray(1)


class UVarintType(Type):
    WIRE_TYPE = 0

    @staticmethod
    async def load(source):
        value, shift, quantum = 0, 0, 0x80
        while quantum & 0x80:
            await source.read_into(_uvarint_buffer)
            quantum = _uvarint_buffer[0]
            value = value + ((quantum & 0x7F) << shift)
            shift += 7
        return value

    @staticmethod
    async def dump(value, target):
        shifted = True
        while shifted:
            shifted = value >> 7
            _uvarint_buffer[0] = (value & 0x7F) | (0x80 if shifted else 0x00)
            await target.write(_uvarint_buffer)
            value = shifted


class BoolType(Type):
    WIRE_TYPE = 0

    @staticmethod
    async def load(source):
        return await UVarintType.load(source) != 0

    @staticmethod
    async def dump(value, target):
        await target.write(b'\x01' if value else b'\x00')


class BytesType(Type):
    WIRE_TYPE = 2

    @staticmethod
    async def load(source):
        size = await UVarintType.load(source)
        data = bytearray(size)
        await source.read_into(data)
        return data

    @staticmethod
    async def dump(value, target):
        await UVarintType.dump(len(value), target)
        await target.write(value)


class UnicodeType(Type):
    WIRE_TYPE = 2

    @staticmethod
    async def load(source):
        size = await UVarintType.load(source)
        data = bytearray(size)
        await source.read_into(data)
        return str(data, 'utf-8')

    @staticmethod
    async def dump(value, target):
        data = bytes(value, 'utf-8')
        await UVarintType.dump(len(data), target)
        await target.write(data)


FLAG_REPEATED = const(1)


class MessageType(Type):
    WIRE_TYPE = 2
    FIELDS = {}

    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])

    def __eq__(self, rhs):
        return (self.__class__ is rhs.__class__ and
                self.__dict__ == rhs.__dict__)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.__dict__)

    @classmethod
    async def load(cls, source=None, target=None):
        if target is None:
            target = build_protobuf_message(cls)
        if source is None:
            source = StreamReader()
        try:
            while True:
                fkey = await UVarintType.load(source)
                ftag = fkey >> 3
                wtype = fkey & 7
                if ftag in cls.FIELDS:
                    field = cls.FIELDS[ftag]
                    ftype = field[1]
                    if wtype != ftype.WIRE_TYPE:
                        raise TypeError(
                            'Value of tag %s has incorrect wiretype %s, %s expected.' %
                            (ftag, wtype, ftype.WIRE_TYPE))
                else:
                    ftype = {0: UVarintType, 2: BytesType}[wtype]
                    await ftype.load(source)
                    continue
                if issubclass(ftype, MessageType):
                    flen = await UVarintType.load(source)
                    slen = source.set_limit(flen)
                    await ftype.load(source, target)
                    source.set_limit(slen)
                else:
                    fvalue = await ftype.load(source)
                    target.send((field, fvalue))
        except EOFError as e:
            try:
                target.throw(e)
            except StopIteration as e:
                return e.value

    @classmethod
    async def dump(cls, message, target):
        for ftag in cls.FIELDS:
            fname, ftype, fflags = cls.FIELDS[ftag]
            fvalue = getattr(message, fname, None)
            if fvalue is None:
                continue
            key = (ftag << 3) | ftype.WIRE_TYPE
            if fflags & FLAG_REPEATED:
                for svalue in fvalue:
                    await UVarintType.dump(key, target)
                    if issubclass(ftype, MessageType):
                        await BytesType.dump(ftype.dumps(svalue), target)
                    else:
                        await ftype.dump(svalue, target)
            else:
                await UVarintType.dump(key, target)
                if issubclass(ftype, MessageType):
                    await BytesType.dump(ftype.dumps(fvalue), target)
                else:
                    await ftype.dump(fvalue, target)
