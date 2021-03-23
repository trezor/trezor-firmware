from typing import *
from trezor.protobuf import MessageType
T = TypeVar("T", bound=MessageType)


# extmod/rustmods/modtrezorproto.c
def type_for_name(name: str) -> Type[MessageType]:
    """Find the message definition for the given protobuf name."""


# extmod/rustmods/modtrezorproto.c
def type_for_wire(wire_type: int) -> Type[MessageType]:
    """Find the message definition for the given wire type (numeric
    identifier)."""


# extmod/rustmods/modtrezorproto.c
def decode(
    buffer: bytes,
    msg_type: Type[T],
    enable_experimental: bool,
) -> T:
    """Decode data in the buffer into the specified message type."""


# extmod/rustmods/modtrezorproto.c
def encoded_length(msg: MessageType) -> int:
    """Calculate length of encoding of the specified message."""


# extmod/rustmods/modtrezorproto.c
def encode(buffer: bytearray, msg: MessageType) -> int:
    """Encode the message into the specified buffer. Return length of
    encoding."""
