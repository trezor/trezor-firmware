# Describing messages themselves. ----------------------------------------------
from . import protobuf

class TypeMetadataType:

    WIRE_TYPE = 2

    def __init__(self):
        # Field description.
        self.__field_metadata_type = protobuf.MessageType()
        self.__field_metadata_type.add_field(1, 'tag', protobuf.UVarintType, flags=protobuf.Flags.REQUIRED)
        self.__field_metadata_type.add_field(2, 'name', protobuf.BytesType, flags=protobuf.Flags.REQUIRED)
        self.__field_metadata_type.add_field(3, 'type', protobuf.BytesType, flags=protobuf.Flags.REQUIRED)
        self.__field_metadata_type.add_field(4, 'flags', protobuf.UVarintType, flags=protobuf.Flags.REQUIRED)
        self.__field_metadata_type.add_field(5, 'embedded', protobuf.EmbeddedMessage(self))  # Used to describe embedded messages.
        # Metadata message description.
        self.__self_type = protobuf.EmbeddedMessage(protobuf.MessageType())
        self.__self_type.message_type.add_field(1, 'fields', protobuf.EmbeddedMessage(self.__field_metadata_type), flags=(Flags.REPEATED | Flags.REQUIRED))

    def __create_message(self, message_type):
        # Creates a message that contains info about the message_type.
        message, message.fields = self.__self_type(), list()
        for field in iter(message_type):
            field_meta = self.__field_metadata_type()
            field_meta.tag, field_meta.name, field_type, field_meta.flags = field
            field_meta.type = type_str = field_type.__class__.__name__
            if isinstance(field_type, protobuf.EmbeddedMessage):
                field_meta.flags |= protobuf.Flags.EMBEDDED
                field_meta.embedded_metadata = self.__create_message(field_type.message_type)
            elif not type_str.endswith('Type'):
                raise TypeError('Type name of type singleton object should end with \'Type\'. Actual: \'%s\'.' % type_str)
            else:
                field_meta.type = type_str[:-4]
            message.fields.append(field_meta)
        return message

    def dump(self, fp, message_type):
        self.__self_type.dump(fp, self.__create_message(message_type))

    def __restore_type(self, message):
        # Restores a message type by the information in the message.
        message_type, g = protobuf.MessageType(), globals()
        for field in message.fields:
            field_type = field['type']
            if not field_type in g:
                raise TypeError('Primitive type \'%s\' not found in this protobuf module.' % field_type)
            field_info = (field.tag, field.name, g[field_type], field.flags)
            if field.flags & protobuf.Flags.EMBEDDED_MASK == protobuf.Flags.EMBEDDED:
                field_info[3] -= protobuf.Flags.EMBEDDED
                field_info[2] = protobuf.EmbeddedMessage(self.__restore_type(field.embedded))
            message_type.add_field(*field_info)
        return message_type

    def load(self, fp):
        return self.__restore_type(self.__self_type.load(fp))
