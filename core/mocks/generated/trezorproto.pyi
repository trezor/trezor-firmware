from typing import *
from typing_extensions import Self
# XXX
# Note that MessageType "subclasses" are not true subclasses, but instead instances
# of the built-in metaclass MsgDef. MessageType instances are in fact instances of
# the built-in type Msg. That is why isinstance checks do not work, and instead the
# MessageTypeSubclass.is_type_of() method must be used.


# rust/src/protobuf/obj.rs
class MessageType:
    MESSAGE_NAME: ClassVar[str] = "MessageType"
    MESSAGE_WIRE_TYPE: ClassVar[int | None] = None
    @classmethod
    def is_type_of(cls: type[Self], msg: "MessageType") -> TypeGuard[Self]:
        """Identify if the provided message belongs to this type."""
T = TypeVar("T", bound=MessageType)


# rust/src/protobuf/obj.rs
def type_for_name(name: str) -> type[MessageType]:
    """Find the message definition for the given protobuf name."""


# rust/src/protobuf/obj.rs
def type_for_wire(wire_id: int) -> type[MessageType]:
    """Find the message definition for the given wire type (numeric identifier)."""


# rust/src/protobuf/obj.rs
def decode(
    buffer: bytes,
    msg_type: type[T],
    enable_experimental: bool,
) -> T:
    """Decode data in the buffer into the specified message type."""


# rust/src/protobuf/obj.rs
def encoded_length(msg: MessageType) -> int:
    """Calculate length of encoding of the specified message."""


# rust/src/protobuf/obj.rs
def encode(buffer: bytearray | memoryview, msg: MessageType) -> int:
    """Encode the message into the specified buffer. Return length of
    encoding."""
