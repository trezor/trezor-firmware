# Implements the Google's protobuf encoding.
# eigenein (c) 2011
# http://eigenein.me/protobuf/

from uio import BytesIO
import ustruct

# Types. -----------------------------------------------------------------------

class UVarintType:
    # Represents an unsigned Varint type.
    WIRE_TYPE = 0

    @staticmethod
    def dump(fp, value):
        shifted_value = True
        while shifted_value:
            shifted_value = value >> 7
            fp.write(chr((value & 0x7F) | (0x80 if shifted_value != 0 else 0x00)))
            value = shifted_value

    @staticmethod
    def load(fp):
        value, shift, quantum = 0, 0, 0x80
        while (quantum & 0x80) == 0x80:
            quantum = ord(fp.read(1))
            value, shift = value + ((quantum & 0x7F) << shift), shift + 7
        return value

# class UInt32Type(UVarintType): pass

class BoolType:
    # Represents a boolean type. Encodes True as UVarint 1, and False as UVarint 0.
    WIRE_TYPE = 0

    @staticmethod
    def dump(fp, value):
        fp.write('\x01' if value else '\x00')

    @staticmethod
    def load(fp):
        return UVarintType.load(fp) != 0

class BytesType:
    # Represents a raw bytes type.

    WIRE_TYPE = 2

    @staticmethod
    def dump(fp, value):
        UVarintType.dump(fp, len(value))
        fp.write(value)

    @staticmethod
    def load(fp):
        return fp.read(UVarintType.load(fp))

class UnicodeType:
    WIRE_TYPE = 2

    @staticmethod
    def dump(fp, value):
        BytesType.dump(fp, bytes(value, 'utf-8'))

    @staticmethod
    def load(fp):
        return BytesType.load(fp).decode('utf-8', 'strict')

# Messages. --------------------------------------------------------------------

FLAG_SIMPLE = 0
FLAG_REQUIRED = 1
FLAG_REQUIRED_MASK = 1
FLAG_SINGLE = 0
FLAG_REPEATED = 2
FLAG_REPEATED_MASK = 6

class EofWrapper:
    # Wraps a stream to raise EOFError instead of just returning of ''.
    def __init__(self, fp, limit=None):
        self.__fp = fp
        self.__limit = limit

    def read(self, size=None):
        # Reads a string. Raises EOFError on end of stream.
        if self.__limit is not None:
            size = min(size, self.__limit)
            self.__limit -= size
        s = self.__fp.read(size)
        if len(s) == 0:
            raise EOFError()
        return s

# Packs a tag and a wire_type into single int according to the protobuf spec.
_pack_key = lambda tag, wire_type: (tag << 3) | wire_type
# Unpacks a key into a tag and a wire_type according to the protobuf spec.
_unpack_key = lambda key: (key >> 3, key & 7)

class MessageType:
    # Represents a message type.

    def __init__(self):
        # Creates a new message type.
        self.__tags_to_types = dict() # Maps a tag to a type instance.
        self.__tags_to_names = dict() # Maps a tag to a given field name.
        self.__defaults = dict()  # Maps a tag to its default value.
        self.__flags = dict()  # Maps a tag to FLAG_

    def add_field(self, tag, name, field_type, flags=FLAG_SIMPLE, default=None):
        # Adds a field to the message type.
        if tag in self.__tags_to_names or tag in self.__tags_to_types:
            raise ValueError('The tag %s is already used.' % tag)
        if default != None:
            self.__defaults[tag] = default
        self.__tags_to_names[tag] = name
        self.__tags_to_types[tag] = field_type
        self.__flags[tag] = flags
        return self # Allow add_field chaining.

    def __call__(self, **fields):
        # Creates an instance of this message type.
        return Message(self, **fields)

    def __has_flag(self, tag, flag, mask):
        # Checks whether the field with the specified tag has the specified flag.
        return (self.__flags[tag] & mask) == flag

    def dump(self, fp, value):
        if self != value.message_type:
            raise TypeError("Incompatible type")
        for tag, field_type in iter(self.__tags_to_types.items()):
            if self.__tags_to_names[tag] in value.__dict__:
                if self.__has_flag(tag, FLAG_SINGLE, FLAG_REPEATED_MASK):
                    # Single value.
                    UVarintType.dump(fp, _pack_key(tag, field_type.WIRE_TYPE))
                    field_type.dump(fp, getattr(value, self.__tags_to_names[tag]))
                elif self.__has_flag(tag, FLAG_REPEATED, FLAG_REPEATED_MASK):
                    # Repeated value.
                    key = _pack_key(tag, field_type.WIRE_TYPE)
                    # Put it together sequently.
                    for single_value in getattr(value, self.__tags_to_names[tag]):
                        UVarintType.dump(fp, key)
                        field_type.dump(fp, single_value)
            elif self.__has_flag(tag, FLAG_REQUIRED, FLAG_REQUIRED_MASK):
                raise ValueError('The field with the tag %s is required but a value is missing.' % tag)

    def load(self, fp):
        fp = EofWrapper(fp)
        message = self.__call__()
        while True:
            try:
                tag, wire_type = _unpack_key(UVarintType.load(fp))

                if tag in self.__tags_to_types:
                    field_type = self.__tags_to_types[tag]
                    if wire_type != field_type.WIRE_TYPE:
                        raise TypeError(
                            'Value of tag %s has incorrect wiretype %s, %s expected.' % \
                            (tag, wire_type, field_type.WIRE_TYPE))
                    if self.__has_flag(tag, FLAG_SINGLE, FLAG_REPEATED_MASK):
                        # Single value.
                        setattr(message, self.__tags_to_names[tag], field_type.load(fp))
                    elif self.__has_flag(tag, FLAG_REPEATED, FLAG_REPEATED_MASK):
                        # Repeated value.
                        if not self.__tags_to_names[tag] in message.__dict__:
                            setattr(message, self.__tags_to_names[tag], list())
                        getattr(message, self.__tags_to_names[tag]).append(field_type.load(fp))
                else:
                    # Skip this field.

                    # This used to correctly determine the length of unknown tags when loading a message.
                    {0: UVarintType, 2: BytesType}[wire_type].load(fp)

            except EOFError:
                for tag, name in iter(self.__tags_to_names.items()):
                    # Fill in default value if value not set
                    if name not in message.__dict__ and tag in self.__defaults:
                        setattr(message, name, self.__defaults[tag])

                    # Check if all required fields are present.
                    if self.__has_flag(tag, FLAG_REQUIRED, FLAG_REQUIRED_MASK) and not name in message.__dict__:
                        if self.__has_flag(tag, FLAG_REPEATED, FLAG_REPEATED_MASK):
                            setattr(message, name, list())  # Empty list (no values was in input stream). But required field.
                        else:
                            raise ValueError('The field %s (\'%s\') is required but missing.' % (tag, name))
                return message

    def dumps(self, value):
        fp = BytesIO()
        self.dump(fp, value)
        return fp.getvalue()

    def loads(self, buf):
        fp = BytesIO(buf)
        return self.load(fp)

class Message:
    # Represents a message instance.

    def __init__(self, message_type, **fields):
        # Initializes a new instance of the specified message type.
        self.message_type = message_type
        # In micropython, we cannot use self.__dict__.update(fields),
        # iterate fields and assign them directly.
        for key in fields:
            setattr(self, key, fields[key])

    def dump(self, fp):
        # Dumps the message into a write-like object.
        return self.message_type.dump(fp, self)

    def dumps(self):
        # Dumps the message into bytes
        return self.message_type.dumps(self)

# Embedded message. ------------------------------------------------------------

class EmbeddedMessage:
    # Represents an embedded message type.

    WIRE_TYPE = 2

    def __init__(self, message_type):
        # Initializes a new instance. The argument is an underlying message type.
        self.message_type = message_type

    def __call__(self):
        # Creates a message of the underlying message type.
        return self.message_type()

    def dump(self, fp, value):
        BytesType.dump(fp, self.message_type.dumps(value))

    def load(self, fp):
        return self.message_type.load(EofWrapper(fp, UVarintType.load(fp)))  # Limit with embedded message length.
