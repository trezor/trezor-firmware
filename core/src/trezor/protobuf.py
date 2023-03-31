from typing import TYPE_CHECKING

import trezorproto

decode = trezorproto.decode
encode = trezorproto.encode
encoded_length = trezorproto.encoded_length
type_for_name = trezorproto.type_for_name
type_for_wire = trezorproto.type_for_wire

if TYPE_CHECKING:
    # XXX
    # Note that MessageType "subclasses" are not true subclasses, but instead instances
    # of the built-in metaclass MsgDef. MessageType instances are in fact instances of
    # the built-in type Msg. That is why isinstance checks do not work, and instead the
    # MessageTypeSubclass.is_type_of() method must be used.
    from typing import TypeGuard, TypeVar

    T = TypeVar("T", bound="MessageType")

    class MessageType:
        MESSAGE_NAME: str = "MessageType"
        MESSAGE_WIRE_TYPE: int | None = None

        @classmethod
        def is_type_of(cls: type[T], msg: "MessageType") -> TypeGuard[T]:
            """Identify if the provided message belongs to this type."""
            raise NotImplementedError


def load_message_buffer(
    buffer: bytes,
    msg_wire_type: int,
    experimental_enabled: bool = True,
) -> MessageType:
    msg_type = type_for_wire(msg_wire_type)
    return decode(buffer, msg_type, experimental_enabled)


def dump_message_buffer(msg: MessageType) -> bytearray:
    buffer = bytearray(encoded_length(msg))
    encode(buffer, msg)
    return buffer
