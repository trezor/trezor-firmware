from storage.cache_thp import SESSION_ID_LENGTH, TAG_LENGTH
from trezor import log, protobuf, utils
from trezor.wire.message_handler import get_msg_type

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
        buffer: utils.BufferType = _get_buffer_for_read(payload_length, channel_buffer)
        return buffer
    except Exception as e:
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            log.exception(__name__, e)
    raise Exception("Failed to create a buffer for channel")  # TODO handle better


def get_write_buffer(
    buffer: utils.BufferType, msg: protobuf.MessageType
) -> utils.BufferType:
    msg_size = protobuf.encoded_length(msg)
    payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size
    required_min_size = payload_size + CHECKSUM_LENGTH + TAG_LENGTH

    if required_min_size > len(buffer):
        return _get_buffer_for_write(required_min_size, buffer)
    return buffer


def encode_into_buffer(
    buffer: utils.BufferType, msg: protobuf.MessageType, session_id: int
) -> int:
    # cannot write message without wire type
    msg_type = msg.MESSAGE_WIRE_TYPE
    if msg_type is None:
        msg_type = get_msg_type(msg.MESSAGE_NAME)
    assert msg_type is not None

    msg_size = protobuf.encoded_length(msg)
    payload_size = SESSION_ID_LENGTH + MESSAGE_TYPE_LENGTH + msg_size

    _encode_session_into_buffer(memoryview(buffer), session_id)
    _encode_message_type_into_buffer(memoryview(buffer), msg_type, SESSION_ID_LENGTH)
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


def _get_buffer_for_read(
    payload_length: int, existing_buffer: utils.BufferType, max_length=MAX_PAYLOAD_LEN
) -> utils.BufferType:
    length = payload_length + INIT_HEADER_LENGTH
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(
            __name__,
            "get_buffer_for_read - length: %d, %s %s",
            length,
            "existing buffer type:",
            type(existing_buffer),
        )
    if length > max_length:
        raise ThpError("Message too large")

    if length > len(existing_buffer):
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            log.debug(__name__, "Allocating a new buffer")

        from ..thp_main import get_raw_read_buffer

        if length > len(get_raw_read_buffer()):
            if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
                log.debug(
                    __name__,
                    "Required length is %d, where raw buffer has capacity only %d",
                    length,
                    len(get_raw_read_buffer()),
                )
            raise ThpError("Message is too large")

        try:
            payload: utils.BufferType = memoryview(get_raw_read_buffer())[:length]
        except MemoryError:
            payload = memoryview(get_raw_read_buffer())[:PACKET_LENGTH]
            raise ThpError("Message is too large")
        return payload

    # reuse a part of the supplied buffer
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(__name__, "Reusing already allocated buffer")
    return memoryview(existing_buffer)[:length]


def _get_buffer_for_write(
    payload_length: int, existing_buffer: utils.BufferType, max_length=MAX_PAYLOAD_LEN
) -> utils.BufferType:
    length = payload_length + INIT_HEADER_LENGTH
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(
            __name__,
            "get_buffer_for_write - length: %d, %s %s",
            length,
            "existing buffer type:",
            type(existing_buffer),
        )
    if length > max_length:
        raise ThpError("Message too large")

    if length > len(existing_buffer):
        if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
            log.debug(__name__, "Creating a new write buffer from raw write buffer")

        from ..thp_main import get_raw_write_buffer

        if length > len(get_raw_write_buffer()):
            raise ThpError("Message is too large")

        try:
            payload: utils.BufferType = memoryview(get_raw_write_buffer())[:length]
        except MemoryError:
            payload = memoryview(get_raw_write_buffer())[:PACKET_LENGTH]
            raise ThpError("Message is too large")
        return payload

    # reuse a part of the supplied buffer
    if __debug__ and utils.ALLOW_DEBUG_MESSAGES:
        log.debug(__name__, "Reusing already allocated buffer")
    return memoryview(existing_buffer)[:length]
