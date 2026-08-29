from typing import *
from buffer_types import *
from trezorproto import MessageType
T = TypeVar("T", bound=MessageType)


# rust/src/definitions/obj.rs
def decode(
    definition: AnyBytes,
    expected_type: int,
    msg_type: type[T],
) -> T:
    """Parse a signed definition blob, verify its signature and decode it
    into the specified message type."""
