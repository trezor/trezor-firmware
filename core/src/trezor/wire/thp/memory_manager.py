from micropython import const
from typing import TYPE_CHECKING
from ustruct import pack_into

from storage.cache_thp import SESSION_ID_LENGTH
from trezor import protobuf

if TYPE_CHECKING:
    from buffer_types import AnyBuffer

MESSAGE_TYPE_LENGTH = const(2)
TAG_LENGTH = const(16)

# Reserve 8.5 kB. AuthenticityProof requires about 8500 bytes.
_PROTOBUF_BUFFER_SIZE = const(8704)

if __debug__:
    from trezor import log


class ThpBuffer:
    def __init__(self) -> None:
        self.buf = memoryview(bytearray(_PROTOBUF_BUFFER_SIZE))

    def get(self, length: int) -> memoryview:
        assert length >= 0
        if length > len(self.buf):
            if __debug__:
                log.warning(
                    __name__,
                    "Failed to get a buffer - requested length (%d) is too big.",
                    length,
                )
            # Try allocating, raises MemoryError on failure.
            return memoryview(bytearray(length))
        return self.buf[:length]


def buffer_size(msg: protobuf.MessageType) -> int:
    return (
        SESSION_ID_LENGTH
        + MESSAGE_TYPE_LENGTH
        + protobuf.encoded_length(msg)
        + TAG_LENGTH
    )


def encode_into_buffer(
    buffer: AnyBuffer, msg: protobuf.MessageType, session_id: int
) -> int:
    """Encode protobuf message `msg` into the `buffer`, including session id
    an messages's wire type. Will fail if provided message has no wire type."""

    # cannot write message without wire type
    msg_type = msg.MESSAGE_WIRE_TYPE
    if msg_type is None:
        raise Exception("Message has no wire type.")

    header_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH
    pack_into(">BH", buffer, 0, session_id, msg_type)
    msg_size = protobuf.encode(memoryview(buffer)[header_size:], msg)

    return header_size + msg_size
