'''
Streaming protobuf codec.

Handles asynchronous encoding and decoding of protobuf value streams.

Value format: ((field_type, field_flags, field_name), field_value)
    field_type: Either one of UVarintType, BoolType, BytesType, UnicodeType,
                or an instance of EmbeddedMessage.
    field_flags (int): Field bit flags `FLAG_REQUIRED`, `FLAG_REPEATED`.
    field_name (str): Field name string.
    field_value: Depends on field_type.  EmbeddedMessage has
                 `field_value == None`.

Type classes are either scalar or message-like (`MessageType`,
`EmbeddedMessage`).  `load()` generators of scalar types end the value,
message types stream it to a target generator as described above.  All
types can be loaded and dumped synchronously with `loads()` and `dumps()`.
'''

from micropython import const
from streams import StreamReader, BufferWriter


def build_protobuf_message(message_type, callback=None, *args):
    message = message_type()
    try:
        while True:
            field, field_value = yield
            field_type, field_flags, field_name = field
            if not _is_scalar_type(field_type):
                field_value = yield from build_protobuf_message(field_type)
            if field_flags & FLAG_REPEATED:
                prev_value = getattr(message, field_name, [])
                prev_value.append(field_value)
                field_value = prev_value
            setattr(message, field_name, field_value)
    except EOFError:
        if callback is not None:
            callback(message, *args)
        return message


class ScalarType:

    @classmethod
    def dumps(cls, value):
        target = BufferWriter()
        dumper = cls.dump(target, value)
        try:
            while True:
                dumper.send(None)
        except StopIteration:
            return target.buffer

    @classmethod
    def loads(cls, value):
        source = StreamReader(value, len(value))
        loader = cls.load(source)
        try:
            while True:
                loader.send(None)
        except StopIteration as e:
            return e.value


_uvarint_buffer = bytearray(1)


class UVarintType(ScalarType):
    WIRE_TYPE = 0

    @staticmethod
    async def dump(target, value):
        shifted = True
        while shifted:
            shifted = value >> 7
            _uvarint_buffer[0] = (value & 0x7F) | (0x80 if shifted else 0x00)
            await target.write(_uvarint_buffer)
            value = shifted

    @staticmethod
    async def load(source):
        value, shift, quantum = 0, 0, 0x80
        while quantum & 0x80:
            await source.read_into(_uvarint_buffer)
            quantum = _uvarint_buffer[0]
            value = value + ((quantum & 0x7F) << shift)
            shift += 7
        return value


class BoolType(ScalarType):
    WIRE_TYPE = 0

    @staticmethod
    async def dump(target, value):
        await target.write(b'\x01' if value else b'\x00')

    @staticmethod
    async def load(source):
        return await UVarintType.load(source) != 0


class BytesType(ScalarType):
    WIRE_TYPE = 2

    @staticmethod
    async def dump(target, value):
        await UVarintType.dump(target, len(value))
        await target.write(value)

    @staticmethod
    async def load(source):
        size = await UVarintType.load(source)
        data = bytearray(size)
        await source.read_into(data)
        return data


class UnicodeType(ScalarType):
    WIRE_TYPE = 2

    @staticmethod
    async def dump(target, value):
        data = bytes(value, 'utf-8')
        await UVarintType.dump(target, len(data))
        await target.write(data)

    @staticmethod
    async def load(source):
        size = await UVarintType.load(source)
        data = bytearray(size)
        await source.read_into(data)
        return str(data, 'utf-8')


class EmbeddedMessage:
    WIRE_TYPE = 2

    def __init__(self, message_type):
        '''Initializes a new instance. The argument is an underlying message type.'''
        self.message_type = message_type

    def __call__(self):
        '''Creates a message of the underlying message type.'''
        return self.message_type()

    async def dump(self, target, value):
        buf = self.message_type.dumps(value)
        await BytesType.dump(target, buf)

    async def load(self, target, source):
        emb_size = await UVarintType.load(source)
        rem_limit = source.with_limit(emb_size)
        result = await self.message_type.load(source, target)
        source.with_limit(rem_limit)
        return result


FLAG_SIMPLE = const(0)
FLAG_REQUIRED = const(1)
FLAG_REPEATED = const(2)


def _pack_key(tag, wire_type):
    '''Pack a tag and a wire_type into single int.'''
    return (tag << 3) | wire_type


def _unpack_key(key):
    '''Unpack a key into a tag and a wire type.'''
    return (key >> 3, key & 7)


def _is_scalar_type(field_type):
    '''Determine if a field type is a scalar or not.'''
    return issubclass(field_type, ScalarType)


class MessageType:
    '''Represents a message type.'''

    def __init__(self, name=None):
        self._name = name
        self._fields = {}  # tag -> tuple of field_type, field_flags, field_name
        self._defaults = {}  # tag -> default_value

    def add_field(self, tag, name, field_type,
                  flags=FLAG_SIMPLE, default=None):
        '''Adds a field to the message type.'''
        if tag in self._fields:
            raise ValueError('The tag %s is already used.' % tag)
        if default is not None:
            self._defaults[tag] = default
        self._fields[tag] = (field_type, flags, name)

    def __call__(self, **fields):
        '''Creates an instance of this message type.'''
        return Message(self, **fields)

    def __repr__(self):
        return '<MessageType: %s>' % self._name

    async def dump(self, target, value):
        if self is not value.message_type:
            raise TypeError('Incompatible type')
        for tag, field in self._fields.items():
            field_type, field_flags, field_name = field
            field_value = getattr(value, field_name, None)
            if field_value is None:
                if field_flags & FLAG_REQUIRED:
                    raise ValueError(
                        'The field with the tag %s is required but a value is missing.' % tag)
                else:
                    continue
            if field_flags & FLAG_REPEATED:
                # repeated value
                key = _pack_key(tag, field_type.WIRE_TYPE)
                # send the values sequentially
                for single_value in field_value:
                    await UVarintType.dump(target, key)
                    await field_type.dump(target, single_value)
            else:
                # single value
                await UVarintType.dump(target, _pack_key(tag, field_type.WIRE_TYPE))
                await field_type.dump(target, field_value)

    async def load(self, target, source=None):
        if source is None:
            source = StreamReader()
        found_tags = set()

        try:
            while True:
                key = await UVarintType.load(source)
                tag, wire_type = _unpack_key(key)
                found_tags.add(tag)

                if tag in self._fields:
                    # retrieve the field descriptor by tag
                    field = self._fields[tag]
                    field_type = field[0]
                    if wire_type != field_type.WIRE_TYPE:
                        raise TypeError(
                            'Value of tag %s has incorrect wiretype %s, %s expected.' %
                            (tag, wire_type, field_type.WIRE_TYPE))
                else:
                    # unknown field, skip it
                    field_type = {0: UVarintType, 2: BytesType}[wire_type]
                    await field_type.load(source)
                    continue

                if _is_scalar_type(field_type):
                    field_value = await field_type.load(source)
                    target.send((field, field_value))
                else:
                    await field_type.load(target, source)

        except EOFError:
            for tag, field in self._fields.items():
                # send the default value
                if tag not in found_tags and tag in self._defaults:
                    target.send((field, self._defaults[tag]))
                    found_tags.add(tag)

                # check if all required fields are present
                _, field_flags, field_name = field
                if field_flags & FLAG_REQUIRED and tag not in found_tags:
                    if field_flags & FLAG_REPEATED:
                        # no values were in input stream, but required field.
                        # send empty list
                        target.send((field, []))
                    else:
                        raise ValueError(
                            'The field %s (\'%s\') is required but missing.' % (tag, field_name))
            try:
                target.throw(EOFError)
            except StopIteration as e:
                return e.value

    def dumps(self, value):
        target = BufferWriter()
        dumper = self.dump(target, value)
        try:
            while True:
                dumper.send(None)
        except StopIteration:
            return target.buffer

    def loads(self, value):
        builder = build_protobuf_message(self)
        builder.send(None)
        source = StreamReader(value, len(value))
        loader = self.load(builder, source)
        try:
            while True:
                loader.send(None)
        except StopIteration as e:
            return e.value


class Message:
    '''Represents a message instance.'''

    def __init__(self, message_type, **fields):
        '''Initializes a new instance of the specified message type.'''
        self.message_type = message_type
        for key in fields:
            setattr(self, key, fields[key])

    async def dump(self, target):
        return await self.message_type.dump(target, self)

    def dumps(self):
        return self.message_type.dumps(self)

    def __repr__(self):
        values = self.__dict__
        values = {k: values[k] for k in values if k != 'message_type'}
        return '<%s: %s>' % (self.message_type._name, values)
