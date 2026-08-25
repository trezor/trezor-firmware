"""THP's use of the wire buffers, plus its own app-header framing.

The two-tier buffer machinery itself is transport-neutral and lives in `trezor.wire.buffers` --
the V1 codec's WARD service interface needs exactly the same thing, and this module cannot be
imported in a codec build at all, because it reaches for `trezorthp`.
"""

from struct import pack_into
from typing import TYPE_CHECKING

from trezor import protobuf
from trezorthp import APP_HEADER_LEN, SEND_BUFFER_OVERHEAD

if TYPE_CHECKING:
    from buffer_types import AnyBuffer


def buffer_size(msg: protobuf.MessageType) -> int:
    return SEND_BUFFER_OVERHEAD + protobuf.encoded_length(msg)


def encode_into_buffer(
    buffer: AnyBuffer, msg: protobuf.MessageType, session_id: int
) -> int:
    """Encode protobuf message `msg` into the `buffer`, including session id
    an messages's wire type. Will fail if provided message has no wire type."""

    # cannot write message without wire type
    msg_type = msg.MESSAGE_WIRE_TYPE
    if msg_type is None:
        raise Exception("Message has no wire type.")

    pack_into(">BH", memoryview(buffer)[:APP_HEADER_LEN], 0, session_id, msg_type)
    msg_size = protobuf.encode(memoryview(buffer)[APP_HEADER_LEN:], msg)

    return APP_HEADER_LEN + msg_size
