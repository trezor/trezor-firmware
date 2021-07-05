import protobuf
import storage.cache
from trezor import messages, utils
from trezor.messages import MessageType

if False:
    from typing import Iterable

WIRE_TYPES: dict[int, tuple[int, ...]] = {
    MessageType.AuthorizeCoinJoin: (MessageType.SignTx, MessageType.GetOwnershipProof),
}


def is_set() -> bool:
    return bool(storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE))


def set(auth_message: protobuf.MessageType) -> None:
    buffer = bytearray(protobuf.count_message(auth_message))
    writer = utils.BufferWriter(buffer)
    protobuf.dump_message(writer, auth_message)
    storage.cache.set(
        storage.cache.APP_COMMON_AUTHORIZATION_TYPE,
        auth_message.MESSAGE_WIRE_TYPE.to_bytes(2, "big"),
    )
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_DATA, buffer)


def get() -> protobuf.MessageType | None:
    stored_auth_type = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return None

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    msg_type = messages.get_type(msg_wire_type)
    buffer = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_DATA)
    reader = utils.BufferReader(buffer)

    return protobuf.load_message(reader, msg_type)


def get_wire_types() -> Iterable[int]:
    stored_auth_type = storage.cache.get(storage.cache.APP_COMMON_AUTHORIZATION_TYPE)
    if not stored_auth_type:
        return ()

    msg_wire_type = int.from_bytes(stored_auth_type, "big")
    return WIRE_TYPES.get(msg_wire_type, ())


def clear() -> None:
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_TYPE, b"")
    storage.cache.set(storage.cache.APP_COMMON_AUTHORIZATION_DATA, b"")
