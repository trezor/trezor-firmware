'''Streaming protobuf codec.

Handles asynchronous encoding and decoding of protobuf value streams.

Value format: ((field_type, field_flags, field_name), field_value)
    field_type: Either one of UVarintType, BoolType, BytesType, UnicodeType,
                or an instance of EmbeddedMessage.
    field_flags (int): Field bit flags `FLAG_REQUIRED`, `FLAG_REPEATED`.
    field_name (str): Field name string.
    field_value: Depends on field_type.  EmbeddedMessage has `field_value == None`.
'''

from micropython import const


def build_protobuf_message(message_type, callback, *args):
    message = message_type()
    try:
        while True:
            field, field_value = yield
            field_type, field_flags, field_name = field
            if not _is_scalar_type(field_type):
                field_value = yield from build_protobuf_message(field_type, callback)
            if field_flags & FLAG_REPEATED:
                prev_value = getattr(message, field_name, [])
                prev_value.append(field_value)
                field_value = prev_value
            setattr(message, field_name, field_value)
    except EOFError:
        callback(message, *args)


def print_protobuf_message(message_type):
    print('OPEN', message_type)
    try:
        while True:
            field, field_value = yield
            field_type, _, field_name = field
            if not _is_scalar_type(field_type):
                yield from print_protobuf_message(field_type)
            else:
                print('FIELD', field_name, field_type, field_value)
    except EOFError:
        print('CLOSE', message_type)


_UVARINT_DUMP_BUFFER = bytearray(1)


class UVarintType:
    WIRE_TYPE = 0

    @staticmethod
    async def dump(target, value):
        shifted = True
        while shifted:
            shifted = value >> 7
            _UVARINT_DUMP_BUFFER[0] = (value & 0x7F) | (
                0x80 if shifted else 0x00)
            await target.write(_UVARINT_DUMP_BUFFER)
            value = shifted

    @staticmethod
    async def load(source):
        value, shift, quantum = 0, 0, 0x80
        while (quantum & 0x80) == 0x80:
            buffer = await source.read(1)
            quantum = buffer[0]
            value = value + ((quantum & 0x7F) << shift)
            shift += 7
        return value


class BoolType:
    WIRE_TYPE = 0

    @staticmethod
    async def dump(target, value):
        await target.write(b'\x01' if value else b'\x00')

    @staticmethod
    async def load(source):
        varint = await UVarintType.load(source)
        return varint != 0


class BytesType:
    WIRE_TYPE = 2

    @staticmethod
    async def dump(target, value):
        await UVarintType.dump(target, len(value))
        await target.write(value)

    @staticmethod
    async def load(source):
        size = await UVarintType.load(source)
        data = await source.read(size)
        return data


class UnicodeType:
    WIRE_TYPE = 2

    @staticmethod
    async def dump(target, value):
        await BytesType.dump(target, bytes(value, 'utf-8'))

    @staticmethod
    async def load(source):
        data = await BytesType.load(source)
        return str(data, 'utf-8', 'strict')


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
        emb_source = source.trim(emb_size)
        await self.message_type.load(emb_source, target)


FLAG_SIMPLE = const(0)
FLAG_REQUIRED = const(1)
FLAG_REPEATED = const(2)


# Packs a tag and a wire_type into single int according to the protobuf spec.
_pack_key = lambda tag, wire_type: (tag << 3) | wire_type
# Unpacks a key into a tag and a wire_type according to the protobuf spec.
_unpack_key = lambda key: (key >> 3, key & 7)
# Determines if a field type is a scalar or not.
_is_scalar_type = lambda field_type: not isinstance(
    field_type, EmbeddedMessage)


class StreamReader:

    def __init__(self, buf=None, limit=None):
        self.buf = buf if buf is not None else bytearray()
        self.limit = limit

    def read(self, n):
        if self.limit is not None:
            if self.limit < n:
                raise EOFError()
            self.limit -= n

        buf = self.buf
        while len(buf) < n:
            chunk = yield
            buf.extend(chunk)

        # TODO: is this the most officient way?
        result = buf[:n]
        buf[:] = buf[n:]
        return result

    def trim(self, limit):
        return StreamReader(self.buf, limit)


class StreamWriter:

    def __init__(self):
        self.buffer = bytearray()

    async def write(self, b):
        self.buffer.extend(b)


class MessageType:
    '''Represents a message type.'''

    def __init__(self, name=None):
        self.__name = name
        self.__fields = {}  # tag -> tuple of field_type, field_flags, field_name
        self.__defaults = {}  # tag -> default_value

    def add_field(self, tag, name, field_type, flags=FLAG_SIMPLE, default=None):
        '''Adds a field to the message type.'''
        if tag in self.__fields:
            raise ValueError('The tag %s is already used.' % tag)
        if default is not None:
            self.__defaults[tag] = default
        self.__fields[tag] = (field_type, flags, name)

    def __call__(self, **fields):
        '''Creates an instance of this message type.'''
        return Message(self, **fields)

    def dumps(self, value):
        target = StreamWriter()
        dumper = self.dump(target, value)
        try:
            while True:
                dumper.send(None)
        except (StopIteration, EOFError):
            return target.buffer

    async def dump(self, target, value):
        if self is not value.message_type:
            raise TypeError('Incompatible type')
        for tag, field in self.__fields.items():
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

    def loads(self, value):
        result = None

        def callback(message):
            nonlocal result
            result = message
        target = build_protobuf_message(self, callback)
        target.send(None)
        # TODO: avoid the copy!
        source = StreamReader(bytearray(value), len(value))
        loader = self.load(target, source)
        try:
            while True:
                loader.send(None)
        except (StopIteration, EOFError):
            if result is None:
                raise Exception('Failed to parse protobuf message')
            return result

    async def load(self, target, source=None):
        if source is None:
            source = StreamReader()
        found_tags = set()

        try:
            while True:
                key = await UVarintType.load(source)
                tag, wire_type = _unpack_key(key)
                found_tags.add(tag)

                if tag in self.__fields:
                    # retrieve the field descriptor by tag
                    field = self.__fields[tag]
                    field_type, _, _ = field
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
            for tag, field in self.__fields.items():
                # send the default value
                if tag not in found_tags and tag in self.__defaults:
                    target.send((field, self.__defaults[tag]))
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
            target.throw(EOFError)

    def __repr__(self):
        return '<MessageType: %s>' % self.__name


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
        return '<%s: %s>' % (self.message_type.__name, values)
