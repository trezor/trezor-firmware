'''Streaming protobuf codec.

Handles asynchronous encoding and decoding of protobuf value streams.

Value format: ((field_type, field_flags, field_name), field_value)
    field_type: Either one of UVarintType, BoolType, BytesType, UnicodeType,
                or an instance of EmbeddedMessage.
    field_flags (int): Field bit flags `FLAG_REQUIRED`, `FLAG_REPEATED`.
    field_name (str): Field name string.
    field_value: Depends on field_type.  EmbeddedMessage has `field_value == None`.
'''


def build_protobuf_message(message_type, future):
    message = message_type()
    try:
        while True:
            field, field_value = yield
            field_type, field_flags, field_name = field
            if not _is_scalar_type(field_type):
                field_value = yield from build_protobuf_message(field_type, future)
            if field_flags & FLAG_REPEATED:
                field_value = getattr(
                    message, field_name, []).append(field_value)
            setattr(message, field_name, field_value)
    except EOFError:
        future.resolve(message)


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


class UVarintType:
    WIRE_TYPE = 0

    @staticmethod
    def dump(target, value):
        shifted_value = True
        while shifted_value:
            shifted_value = value >> 7
            yield from target.write(chr((value & 0x7F) | (
                0x80 if shifted_value != 0 else 0x00)))
            value = shifted_value

    @staticmethod
    def load(source):
        value, shift, quantum = 0, 0, 0x80
        while (quantum & 0x80) == 0x80:
            data = yield from source.read(1)
            quantum = ord(data)
            value, shift = value + ((quantum & 0x7F) << shift), shift + 7
        return value


class BoolType:
    WIRE_TYPE = 0

    @staticmethod
    def dump(target, value):
        yield from target.write('\x01' if value else '\x00')

    @staticmethod
    def load(source):
        varint = yield from UVarintType.load(source)
        return varint != 0


class BytesType:
    WIRE_TYPE = 2

    @staticmethod
    def dump(target, value):
        yield from UVarintType.dump(target, len(value))
        yield from target.write(value)

    @staticmethod
    def load(source):
        size = yield from UVarintType.load(source)
        data = yield from source.read(size)
        return data


class UnicodeType:
    WIRE_TYPE = 2

    @staticmethod
    def dump(target, value):
        yield from BytesType.dump(target, bytes(value, 'utf-8'))

    @staticmethod
    def load(source):
        data = yield from BytesType.load(source)
        return data.decode('utf-8', 'strict')


class EmbeddedMessage:
    WIRE_TYPE = 2

    def __init__(self, message_type):
        '''Initializes a new instance. The argument is an underlying message type.'''
        self.message_type = message_type

    def __call__(self):
        '''Creates a message of the underlying message type.'''
        return self.message_type()

    def dump(self, target, value):
        buf = self.message_type.dumps(value)
        yield from BytesType.dump(target, buf)

    def load(self, source, target):
        emb_size = yield from UVarintType.load(source)
        emb_source = source.limit(emb_size)
        yield from self.message_type.load(emb_source, target)


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


class AsyncBytearrayWriter:

    def __init__(self):
        self.buf = bytearray()

    async def write(self, b):
        self.buf.extend(b)


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
        target = AsyncBytearrayWriter()
        yield from self.dump(target, value)
        return target.buf

    def dump(self, target, value):
        if self is not value.message_type:
            raise TypeError('Incompatible type')
        for tag, field in self.__fields.items():
            field_type, field_flags, field_name = field
            if field_name not in value.__dict__:
                if field_flags & FLAG_REQUIRED:
                    raise ValueError(
                        'The field with the tag %s is required but a value is missing.' % tag)
                else:
                    continue
            if field_flags & FLAG_REPEATED:
                # repeated value
                key = _pack_key(tag, field_type.WIRE_TYPE)
                # send the values sequentially
                for single_value in getattr(value, field_name):
                    yield from UVarintType.dump(target, key)
                    yield from field_type.dump(target, single_value)
            else:
                # single value
                yield from UVarintType.dump(target, _pack_key(tag, field_type.WIRE_TYPE))
                yield from field_type.dump(target, getattr(value, field_name))

    def load(self, source, target):
        found_tags = set()

        try:
            while True:
                key = yield from UVarintType.load(source)
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
                    yield from field_type.load(source)
                    continue

                if _is_scalar_type(field_type):
                    field_value = yield from field_type.load(source)
                    target.send((field, field_value))
                else:
                    yield from field_type.load(source, target)

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

    def dump(self, target):
        yield from self.message_type.dump(target, self)

    def __repr__(self):
        values = self.__dict__
        values = {k: values[k] for k in values if k != 'message_type'}
        return '<%s: %s>' % (self.message_type.__name, values)
