from storage.cache_thp import SESSION_ID_LENGTH, TAG_LENGTH
from trezor import log, protobuf, utils

from . import ChannelState, ThpError
from .checksum import CHECKSUM_LENGTH
from .writer import (
    INIT_HEADER_LENGTH,
    MAX_PAYLOAD_LEN,
    MESSAGE_TYPE_LENGTH,
    PACKET_LENGTH,
)


def select_buffer(
    channel_state: int,
    channel_buffer: utils.BufferType,
    packet_payload: utils.BufferType,
    payload_length: int,
) -> utils.BufferType:

    if channel_state is ChannelState.ENCRYPTED_TRANSPORT:
        session_id = packet_payload[0]
        if session_id == 0:
            pass
            # TODO use small buffer
        else:
            pass
            # TODO use big buffer but only if the channel owns the buffer lock.
            # Otherwise send BUSY message and return
    else:
        pass
        # TODO use small buffer
    try:
        # TODO for now, we create a new big buffer every time. It should be changed
        buffer: utils.BufferType = _get_buffer_for_message(
            payload_length, channel_buffer
        )
        return buffer
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
    raise Exception("Failed to create a buffer for channel")  # TODO handle better


def get_write_buffer(
    buffer: utils.BufferType, msg: protobuf.MessageType
) -> utils.BufferType:
    msg_size = protobuf.encoded_length(msg)
    payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
    required_min_size = payload_size + CHECKSUM_LENGTH + TAG_LENGTH

    if required_min_size > len(buffer):
        # message is too big, we need to allocate a new buffer
        return bytearray(required_min_size)
    return buffer


def encode_into_buffer(
    buffer: utils.BufferType, msg: protobuf.MessageType, session_id: int
) -> int:

    # cannot write message without wire type
    assert msg.MESSAGE_WIRE_TYPE is not None

    msg_size = protobuf.encoded_length(msg)
    payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size

    _encode_session_into_buffer(memoryview(buffer), session_id)
    _encode_message_type_into_buffer(
        memoryview(buffer), msg.MESSAGE_WIRE_TYPE, SESSION_ID_LENGTH
    )
    _encode_message_into_buffer(
        memoryview(buffer), msg, SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH
    )

    return payload_size


def _encode_session_into_buffer(
    buffer: memoryview, session_id: int, buffer_offset: int = 0
) -> None:
    session_id_bytes = int.to_bytes(session_id, SESSION_ID_LENGTH, "big")
    utils.memcpy(buffer, buffer_offset, session_id_bytes, 0)


def _encode_message_type_into_buffer(
    buffer: memoryview, message_type: int, offset: int = 0
) -> None:
    msg_type_bytes = int.to_bytes(message_type, MESSAGE_TYPE_LENGTH, "big")
    utils.memcpy(buffer, offset, msg_type_bytes, 0)


def _encode_message_into_buffer(
    buffer: memoryview, message: protobuf.MessageType, buffer_offset: int = 0
) -> None:
    protobuf.encode(memoryview(buffer[buffer_offset:]), message)


def _get_buffer_for_message(
    payload_length: int, existing_buffer: utils.BufferType, max_length=MAX_PAYLOAD_LEN
) -> utils.BufferType:
    length = payload_length + INIT_HEADER_LENGTH
    if __debug__:
        log.debug(
            __name__,
            "get_buffer_for_message - length: %d, %s %s",
            length,
            "existing buffer type:",
            type(existing_buffer),
        )
    if length > max_length:
        raise ThpError("Message too large")

    if length > len(existing_buffer):
        # allocate a new buffer to fit the message
        try:
            payload: utils.BufferType = bytearray(length)
        except MemoryError:
            payload = bytearray(PACKET_LENGTH)
            raise ThpError("Message too large")
        return payload

    # reuse a part of the supplied buffer
    return memoryview(existing_buffer)[:length]
