from micropython import const
from typing import TYPE_CHECKING

from storage.cache_thp import SESSION_ID_LENGTH
from trezor import protobuf, utils

from .writer import MESSAGE_TYPE_LENGTH

if TYPE_CHECKING:
    from buffer_types import AnyBuffer

_PROTOBUF_BUFFER_SIZE = const(8192)


class ThpBuffer:
    def __init__(self) -> None:
        self.buf = memoryview(bytearray(_PROTOBUF_BUFFER_SIZE))

    def get(self, length: int) -> memoryview:
        assert length <= len(self.buf)
        return self.buf[:length]


def encode_into_buffer(
    buffer: AnyBuffer, msg: protobuf.MessageType, session_id: int
) -> int:
    """Encode protobuf message `msg` into the `buffer`, including session id
    an messages's wire type. Will fail if provided message has no wire type."""

    # cannot write message without wire type
    msg_type = msg.MESSAGE_WIRE_TYPE
    if msg_type is None:
        raise Exception("Message has no wire type.")

    msg_size = protobuf.encoded_length(msg)
    payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size

    _encode_session_into_buffer(memoryview(buffer), session_id)
    _encode_message_type_into_buffer(memoryview(buffer), msg_type, SESSION_ID_LENGTH)
    _encode_message_into_buffer(
        memoryview(buffer), msg, SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH
    )

    return payload_size


def _encode_session_into_buffer(
    buffer: AnyBuffer, session_id: int, buffer_offset: int = 0
) -> None:
    session_id_bytes = int.to_bytes(session_id, SESSION_ID_LENGTH, "big")
    utils.memcpy(buffer, buffer_offset, session_id_bytes, 0)


def _encode_message_type_into_buffer(
    buffer: AnyBuffer, message_type: int, offset: int = 0
) -> None:
    msg_type_bytes = int.to_bytes(message_type, MESSAGE_TYPE_LENGTH, "big")
    utils.memcpy(buffer, offset, msg_type_bytes, 0)


def _encode_message_into_buffer(
    buffer: AnyBuffer, message: protobuf.MessageType, buffer_offset: int = 0
) -> None:
    protobuf.encode(memoryview(buffer[buffer_offset:]), message)
