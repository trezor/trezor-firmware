import utime
from micropython import const

from storage.cache_thp import SESSION_ID_LENGTH
from trezor import protobuf, utils
from trezor.wire.errors import WireBufferError

from . import ThpError
from .writer import MAX_PAYLOAD_LEN, MESSAGE_TYPE_LENGTH

_PROTOBUF_BUFFER_SIZE = 8192
READ_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)
WRITE_BUFFER = bytearray(_PROTOBUF_BUFFER_SIZE)
LOCK_TIMEOUT = 200  # miliseconds


lock_owner_cid: int | None = None
lock_time: int = 0

READ_BUFFER_SLICE: memoryview | None = None
WRITE_BUFFER_SLICE: memoryview | None = None

# Buffer types
_READ: int = const(0)
_WRITE: int = const(1)


#
# Access to buffer slices


def release_lock_if_owner(channel_id: int) -> None:
    global lock_owner_cid
    if lock_owner_cid == channel_id:
        lock_owner_cid = None


def get_new_read_buffer(channel_id: int, length: int) -> memoryview:
    return _get_new_buffer(_READ, channel_id, length)


def get_new_write_buffer(channel_id: int, length: int) -> memoryview:
    return _get_new_buffer(_WRITE, channel_id, length)


def get_existing_read_buffer(channel_id: int) -> memoryview:
    return _get_existing_buffer(_READ, channel_id)


def get_existing_write_buffer(channel_id: int) -> memoryview:
    return _get_existing_buffer(_WRITE, channel_id)


def _get_new_buffer(buffer_type: int, channel_id: int, length: int) -> memoryview:
    if is_locked():
        if not is_owner(channel_id):
            raise WireBufferError
        update_lock_time()
    else:
        update_lock(channel_id)

    if buffer_type == _READ:
        global READ_BUFFER
        buffer = READ_BUFFER
    elif buffer_type == _WRITE:
        global WRITE_BUFFER
        buffer = WRITE_BUFFER
    else:
        raise Exception("Invalid buffer_type")

    if length > MAX_PAYLOAD_LEN or length > len(buffer):
        raise ThpError("Message is too large")  # TODO reword

    if buffer_type == _READ:
        global READ_BUFFER_SLICE
        READ_BUFFER_SLICE = memoryview(READ_BUFFER)[:length]
        return READ_BUFFER_SLICE

    if buffer_type == _WRITE:
        global WRITE_BUFFER_SLICE
        WRITE_BUFFER_SLICE = memoryview(WRITE_BUFFER)[:length]
        return WRITE_BUFFER_SLICE

    raise Exception("Invalid buffer_type")


def _get_existing_buffer(buffer_type: int, channel_id: int) -> memoryview:
    if not is_owner(channel_id):
        raise WireBufferError
    update_lock_time()

    if buffer_type == _READ:
        global READ_BUFFER_SLICE
        if READ_BUFFER_SLICE is None:
            raise WireBufferError
        return READ_BUFFER_SLICE

    if buffer_type == _WRITE:
        global WRITE_BUFFER_SLICE
        if WRITE_BUFFER_SLICE is None:
            raise WireBufferError
        return WRITE_BUFFER_SLICE

    raise Exception("Invalid buffer_type")


#
# Buffer locking


def is_locked() -> bool:
    global lock_owner_cid
    global lock_time

    time_diff = utime.ticks_diff(utime.ticks_ms(), lock_time)
    return lock_owner_cid is not None and time_diff < LOCK_TIMEOUT


def is_owner(channel_id: int) -> bool:
    global lock_owner_cid
    return lock_owner_cid is not None and lock_owner_cid == channel_id


def update_lock(channel_id: int) -> None:
    set_owner(channel_id)
    update_lock_time()


def set_owner(channel_id: int) -> None:
    global lock_owner_cid
    lock_owner_cid = channel_id


def update_lock_time() -> None:
    global lock_time
    lock_time = utime.ticks_ms()


#
# Helper for encoding messages into buffer


def encode_into_buffer(
    buffer: utils.BufferType, msg: protobuf.MessageType, session_id: int
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
